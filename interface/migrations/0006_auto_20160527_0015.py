# -*- coding: utf-8 -*-
# Generated by Django 1.9.6 on 2016-05-27 07:15
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('interface', '0005_auto_20160526_0155'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='build',
            options={'ordering': ['-created_at']},
        ),
        migrations.AlterModelOptions(
            name='repo',
            options={'ordering': ['full_name']},
        ),
        migrations.AlterField(
            model_name='repo',
            name='webhook_id',
            field=models.IntegerField(blank=True, null=True),
        ),
    ]
