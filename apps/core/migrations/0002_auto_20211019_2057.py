# Generated by Django 3.0 on 2021-10-20 00:57

from django.db import migrations
import jsonfield.fields


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='typenews',
            name='template',
            field=jsonfield.fields.JSONField(default=list),
        ),
    ]
