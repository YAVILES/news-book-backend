# Generated by Django 3.2.12 on 2022-04-22 15:54

from django.db import migrations
import timezone_field.fields


class Migration(migrations.Migration):

    dependencies = [
        ('customers', '0003_client_email'),
    ]

    operations = [
        migrations.AddField(
            model_name='client',
            name='timezone',
            field=timezone_field.fields.TimeZoneField(default='UTC'),
        ),
    ]