from django.conf import settings
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.db import models
from github import UnknownObjectException
from social.apps.django_app.default.models import UserSocialAuth

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
