from django.contrib.auth.models import User
from django.db import models

from interface.utils import get_github


class Repo(models.Model):
    user = models.ForeignKey(User, related_name='repos')
    full_name = models.TextField()
    webhook_id = models.IntegerField(null=True, blank=True)
    is_private = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def get_head_build(self):
        return Build.objects.filter(repo=self, ref='master').only('status').first()

    def soft_delete(self):
        g = get_github(self.user)
        hook = g.get_repo(self.full_name).get_hook(self.webhook_id)
        hook.delete()

        self.webhook_id = None
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
    result = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    @property
    def short_sha(self):
        return self.sha[:7]

    class Meta:
        ordering = ['-created_at']
