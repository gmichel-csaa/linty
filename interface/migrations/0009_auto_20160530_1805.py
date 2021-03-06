# -*- coding: utf-8 -*-
# Generated by Django 1.9.6 on 2016-05-31 01:05
from __future__ import unicode_literals

from django.db import migrations


def migrate_results(apps, schema_editor):
    Build = apps.get_model('interface', 'Build')
    Result = apps.get_model('interface', 'Result')
    for build in Build.objects.all():
        Result.objects.create(
            build=build,
            linter='PEP8',
            output=build.result_old
        )


class Migration(migrations.Migration):

    dependencies = [
        ('interface', '0008_auto_20160530_1805'),
    ]

    operations = [
        migrations.RunPython(migrate_results),
    ]
