import os
import shutil
import subprocess

import django_rq
import requests
from django.conf import settings
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.db import models
from django.templatetags.static import static
from django.utils import timezone
from github import UnknownObjectException
from social.apps.django_app.default.models import UserSocialAuth

from interface import linters
from interface.linters import LINTER_CHOICES
from interface.tasks import build_handler
from interface.utils import get_github


class UserProxy(User):
    class Meta:
        proxy = True

    def get_auth(self):
        try:
            data = UserSocialAuth.objects.filter(user=self).values_list('extra_data')[0][0]
        except:
            return None

        username = data['login']
        password = data['access_token']
        return (username, password)


class Repo(models.Model):
    user = models.ForeignKey(UserProxy, related_name='repos')
    full_name = models.TextField(unique=True)
    webhook_id = models.IntegerField(null=True, blank=True)
    is_private = models.BooleanField(default=True)
    default_branch = models.TextField(default='master')

    disabled = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.full_name

    def get_absolute_url(self):
        return reverse('repo_detail', kwargs={'full_name': self.full_name})

    @property
    def clone_url(self):
        return 'https://github.com/{}.git'.format(self.full_name)

    def get_head_build(self):
        return Build.objects.filter(repo=self, ref=self.default_branch).only('status').first()

    def soft_delete(self):
        self.disabled = True
        self.remove_webhook()

    def remove_webhook(self):
        if not settings.DEBUG:
            g = get_github(self.user)
            grepo = g.get_repo(self.full_name)

            try:
                hook = grepo.get_hook(self.webhook_id)
                hook.delete()
            except UnknownObjectException:
                pass

        self.webhook_id = None
        self.save()

    def user_is_collaborator(self, user):
        if not user.is_authenticated():
            return False
        if self.user == user or user.is_staff:
            return True
        g = get_github(user)
        grepo = g.get_repo(self.full_name)
        guser = g.get_user(user.username)
        return grepo.has_in_collaborators(guser)

    def add_webhook(self, request):
        if settings.DEBUG:
            self.webhook_id = 123
        else:
            g = get_github(self.user)
            grepo = g.get_repo(self.full_name)

            hook = grepo.create_hook(
                'web',
                {
                    'content_type': 'json',
                    'url': request.build_absolute_uri(reverse('webhook')),
                    'secret': settings.WEBHOOK_SECRET
                },
                events=['push'],
                active=True
            )
            self.webhook_id = hook.id

        self.save()

    class Meta:
        ordering = ['full_name']


class Build(models.Model):
    SUCCESS = 'success'
    ERROR = 'error'
    PENDING = 'pending'
    CANCELLED = 'cancelled'

    STATUS_CHOICES = (
        (SUCCESS, SUCCESS),
        (ERROR, ERROR),
        (PENDING, PENDING),
        (CANCELLED, CANCELLED)
    )

    repo = models.ForeignKey(Repo, related_name='builds')
    ref = models.TextField()
    sha = models.TextField()
    status = models.TextField(choices=STATUS_CHOICES, default=PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.short_sha

    @property
    def status_url(self):
        return 'https://api.github.com/repos/{full_name}/statuses/{sha}'.format(
            full_name=self.repo.full_name,
            sha=self.sha
        )

    @property
    def meta_description(self):
        desc = '{0} '.format(self.short_sha)
        if self.status == 'success':
            desc += 'passed linting!'
        elif self.status == 'pending':
            desc += 'is still being linted.'
        else:
            desc += 'failed linting. See failures here.'
        return desc

    @property
    def meta_image(self):
        if self.status == 'success':
            url = static('img/pass.png')
        elif self.status == 'pending':
            url = static('img/pending.png')
        else:
            url = static('img/fail.png')
        return url

    def publish_status(self, auth, state, description):
        hostname = settings.HOSTNAME
        build_url = reverse('build_detail', kwargs={'pk': self.id})
        details_url = 'https://{0}{1}'.format(hostname, build_url)
        data = {
            'state': state,
            'description': description,
            'target_url': details_url,
            'context': 'linty'
        }
        requests.post(self.status_url, json=data, auth=auth)

    def set_status(self, auth, state):
        message = ''
        if state == self.PENDING:
            message = 'Linting your code...'
        elif state == self.SUCCESS:
            message = 'Your code passed linting.'
            self.finished_at = timezone.now()
        elif state == self.ERROR:
            message = 'Your code has lint failures. See Details.'
            self.finished_at = timezone.now()
        elif state == self.CANCELLED:
            message = 'An error occurred while linting.'
            self.finished_at = timezone.now()
        if self.status != state:
            self.status = state
            self.save()
        if not settings.DEBUG and self.repo.webhook_id:
            self.publish_status(auth, state, message)

    def clone(self, auth):
        clone_url = self.repo.clone_url
        clone_url = clone_url.replace('github.com', '{}:{}@github.com'.format(*auth))
        if not os.path.exists('tmp'):
            os.makedirs('tmp')

        self.clean_directory()

        directory = self.directory

        subprocess.call([
            'git', 'clone', clone_url, self.directory
        ])
        subprocess.call([
            'git', '--git-dir=%s/.git' % directory, '--work-tree=%s' % directory, 'fetch', clone_url
        ])
        subprocess.call([
            'git', '--git-dir=%s/.git' % directory, '--work-tree=%s' % directory, 'checkout', self.sha
        ])

    def clean_directory(self):
        if os.path.exists(self.directory):
            shutil.rmtree(self.directory)

    def lint(self):
        return linters.lint(self)

    def enqueue(self, auth):
        self.set_status(auth, Build.PENDING)
        django_rq.enqueue(build_handler, self.id)

    def get_issues(self):
        g = get_github(self.repo.user)
        issues = g.search_issues('%s+repo:%s' % (self.short_sha, self.repo.full_name))
        return issues

    @property
    def short_sha(self):
        return self.sha[:7]

    @property
    def directory(self):
        return 'tmp/%s' % self.sha[:7]

    class Meta:
        ordering = ['-created_at']


class Result(models.Model):
    build = models.ForeignKey(Build, related_name='results')
    linter = models.TextField(choices=LINTER_CHOICES)
    output = models.TextField(null=True, blank=True)
