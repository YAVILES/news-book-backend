import os
from celery import Celery

import os
from django.conf import settings

from tenant_schemas_celery.app import CeleryApp as TenantAwareCeleryApp

# set the default Django settings module for the 'celery' program.
# this is also used in manage.py
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'newsbookbackend.settings')

app = TenantAwareCeleryApp()
app.config_from_object('django.conf:settings')
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)
