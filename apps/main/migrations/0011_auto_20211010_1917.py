# Generated by Django 3.0 on 2021-10-10 23:17

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0010_news_location'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='location',
            name='status',
        ),
        migrations.AddField(
            model_name='location',
            name='is_active',
            field=models.BooleanField(default=True),
        ),
    ]
