# Generated by Django 3.2.12 on 2022-03-28 20:04

import django.contrib.postgres.fields
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('setting', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='notification',
            name='days',
            field=django.contrib.postgres.fields.ArrayField(base_field=models.DateField(), default=list, null=True, size=None, verbose_name='days'),
        ),
        migrations.AlterField(
            model_name='notification',
            name='week_days',
            field=django.contrib.postgres.fields.ArrayField(base_field=models.SmallIntegerField(), default=list, null=True, size=7, verbose_name='week days'),
        ),
    ]