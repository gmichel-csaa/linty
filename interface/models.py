import os
import shutil
import subprocess

import requests
from django.conf import settings
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.db import models
from django.utils import timezone
from github import UnknownObjectException
from social.apps.django_app.default.models import UserSocialAuth

from interface import linters
from interface.linters import LINTER_CHOICES
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

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.full_name

    @property
    def clone_url(self):
        return 'https://github.com/{}.git'.format(self.full_name)

    def get_head_build(self):
        return Build.objects.filter(repo=self, ref='master').only('status').first()

    def soft_delete(self):
        g = get_github(self.user)
        grepo = g.get_repo(self.full_name)

        try:
            assert self.webhook_id
            hook = grepo.get_hook(self.webhook_id)
            hook.delete()
            self.webhook_id = None
        except (UnknownObjectException, AssertionError):
            pass

        self.save()

    def user_is_collaborator(self, user):
        if not user.is_authenticated():
            return False
        if self.user == user:
            return True
        g = get_github(user)
        grepo = g.get_repo(self.full_name)
        guser = g.get_user(user.username)
        return grepo.has_in_collaborators(guser)

    def add_webhook(self, request):
        g = get_github(request.user)
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
        self.is_private = grepo.private
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
        if not settings.DEBUG:
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

    def get_issues(self, user):
        g = get_github(user)
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
