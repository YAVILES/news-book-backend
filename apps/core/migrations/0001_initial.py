# Generated by Django 3.0 on 2021-10-20 01:41

import apps.core.models
from django.db import migrations, models
import jsonfield.fields
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='TypeNews',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created', models.DateTimeField(auto_now_add=True, verbose_name='created')),
                ('updated', models.DateTimeField(auto_now=True, verbose_name='updated')),
                ('code', models.CharField(blank=True, help_text='Código del tipo de novedad', max_length=255, unique=True, verbose_name='code')),
                ('description', models.CharField(help_text='Descripción del tipo de novedad', max_length=255, unique=True, verbose_name='description')),
                ('image', models.ImageField(help_text='Imagen del tipo de novedad', null=True, upload_to=apps.core.models.type_new_path, verbose_name='image')),
                ('info', models.CharField(max_length=255)),
                ('template', jsonfield.fields.JSONField(default=list)),
                ('is_active', models.BooleanField(default=True)),
            ],
            options={
                'abstract': False,
            },
        ),
    ]
