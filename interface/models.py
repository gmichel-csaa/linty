from django.contrib.auth.models import User
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
    full_name = models.TextField()
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
