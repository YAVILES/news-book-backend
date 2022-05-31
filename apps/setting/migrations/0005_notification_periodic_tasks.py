# Generated by Django 3.2.12 on 2022-05-27 17:41

import django.contrib.postgres.fields
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('setting', '0004_remove_notification_periodic_tasks'),
    ]

    operations = [
        migrations.AddField(
            model_name='notification',
            name='periodic_tasks',
            field=django.contrib.postgres.fields.ArrayField(base_field=models.CharField(max_length=255), default=list, null=True, size=None, verbose_name='periodic tasks ids'),
        ),
    ]
