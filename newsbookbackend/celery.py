from __future__ import absolute_import, unicode_literals # for python2

import os

from tenant_schemas_celery.app import CeleryApp as TenantAwareCeleryApp

# from celery import Celery

# set the default Django settings module for the 'celery' program.
# this is also used in manage.py
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'newsbookbackend.settings')


# Get the base REDIS URL, default to redis' default
BASE_REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')

# app = Celery('newsbookbackend')
app = TenantAwareCeleryApp('newsbookbackend')

# Using a string here means the worker don't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django app configs.
app.autodiscover_tasks()

app.conf.broker_url = BASE_REDIS_URL

# this allows you to schedule items in the Django admin.
app.conf.beat_scheduler = 'django_celery_beat.schedulers.DatabaseScheduler'

# Configuración de Tareas Periodicas
'''
from celery.schedules import crontab
app.conf.beat_schedule = {
    'add-clean_unnecessary_records-contrab': {
        'task': 'clean_unnecessary_records',
        'schedule': crontab(15, 0),
        #'args': (16, 16),
    },
}
'''
