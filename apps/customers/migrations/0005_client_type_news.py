# Generated by Django 3.2.12 on 2025-03-06 14:41

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0002_typenews_is_changing_of_the_guard'),
        ('customers', '0004_client_timezone'),
    ]

    operations = [
        migrations.AddField(
            model_name='client',
            name='type_news',
            field=models.ManyToManyField(related_name='clients', to='core.TypeNews', verbose_name='type news'),
        ),
    ]
