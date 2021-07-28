# Generated by Django 3.0 on 2021-07-28 18:34

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('main', '0004_auto_20210723_0012'),
    ]

    operations = [
        migrations.AlterField(
            model_name='news',
            name='created_by',
            field=models.ForeignKey(help_text='Creado por', null=True, on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL, verbose_name='created_by'),
        ),
    ]
