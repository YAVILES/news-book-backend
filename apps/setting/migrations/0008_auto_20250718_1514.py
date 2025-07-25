# Generated by Django 3.2.12 on 2025-07-18 19:14

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0025_accessentry_voucher'),
        ('setting', '0007_auto_20250709_1345'),
    ]

    operations = [
        migrations.AddField(
            model_name='facialrecognitionevent',
            name='location',
            field=models.ForeignKey(help_text='Ubicación o Libro donde se generó el reconocimiento', null=True, on_delete=django.db.models.deletion.PROTECT, to='main.location', verbose_name='location'),
        ),
        migrations.AddField(
            model_name='facialrecognitionevent',
            name='movement_type',
            field=models.CharField(choices=[('IN', 'Entrada'), ('OUT', 'Salida')], default='IN', max_length=3, verbose_name='movement_type'),
        ),
    ]
