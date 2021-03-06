# Generated by Django 3.0 on 2021-11-16 13:56

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('core', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('main', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='news',
            name='created_by',
            field=models.ForeignKey(help_text='Usuario por el que fue crada la novedad', null=True, on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL, verbose_name='created_by'),
        ),
        migrations.AddField(
            model_name='news',
            name='location',
            field=models.ForeignKey(help_text='Ubicación o Libro donde se generó la novedad', null=True, on_delete=django.db.models.deletion.PROTECT, to='main.Location', verbose_name='location'),
        ),
        migrations.AddField(
            model_name='news',
            name='materials',
            field=models.ManyToManyField(related_name='news', through='main.MaterialNews', to='main.Material', verbose_name='materials'),
        ),
        migrations.AddField(
            model_name='news',
            name='people',
            field=models.ManyToManyField(related_name='news', through='main.PersonNews', to='main.Person', verbose_name='people'),
        ),
        migrations.AddField(
            model_name='news',
            name='type_news',
            field=models.ForeignKey(blank=True, help_text='Tipo de la novedad', on_delete=django.db.models.deletion.PROTECT, to='core.TypeNews', verbose_name='type_news'),
        ),
        migrations.AddField(
            model_name='news',
            name='vehicles',
            field=models.ManyToManyField(related_name='news', through='main.VehicleNews', to='main.Vehicle', verbose_name='vehicles'),
        ),
        migrations.AddField(
            model_name='materialnews',
            name='material',
            field=models.ForeignKey(blank=True, on_delete=django.db.models.deletion.PROTECT, to='main.Material', verbose_name='material'),
        ),
        migrations.AddField(
            model_name='materialnews',
            name='news',
            field=models.ForeignKey(blank=True, on_delete=django.db.models.deletion.PROTECT, to='main.News', verbose_name='news'),
        ),
    ]
