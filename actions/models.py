from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models

from interface.models import UserProxy


class Action(models.Model):
    CREATE = 'created'
    DELETE = 'deleted'

    ACTIONS = (
        (CREATE, CREATE),
        (DELETE, DELETE)
    )

    user = models.ForeignKey(UserProxy)
    time = models.DateTimeField(auto_now_add=True)
    action = models.CharField(choices=ACTIONS)

    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')

    def __str__(self):
        return 'User {0} {1} {2}'.format(self.user, self.action, self.content_type)
