import uuid

from django.db import models
import jsonfield
from django_tenants.models import TenantMixin
from django.utils.translation import ugettext_lazy as _

# Create your models here.

PLANNED_STAFF = "PLANNED_STAFF"
PLANNED_PERSONNEL_WITH_SAFETY_PROTOCOL = "PLANNED_PERSONNEL_WITH_SAFETY_PROTOCOL"
CODES_TEMPLATES = (
    (PLANNED_STAFF, "PERSONAL PLANIFICADO IBARTI"),
    (PLANNED_PERSONNEL_WITH_SAFETY_PROTOCOL, "PERSONAL PLANIFICADO IBARTI CON PROTOCOLO DE SEGURIDAD")
)


class ModelBase(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created = models.DateTimeField(verbose_name=_('created'), auto_now_add=True)
    updated = models.DateTimeField(verbose_name=_('updated'), auto_now=True)

    class Meta:
        abstract = True


def type_new_path(type_news: 'TypeNews', file_name):
    return 'img/code/{0}/{1}'.format(type_news.description, file_name)


class TypeNews(ModelBase):
    code = models.CharField(max_length=255, verbose_name="code", blank=True, unique=True,
                            help_text="Código del tipo de novedad")
    description = models.CharField(max_length=255, verbose_name="description", unique=True,
                                   help_text="Descripción del tipo de novedad")
    template = models.CharField(max_length=255, verbose_name="template", help_text="Plantilla del tipo de novedad")
    image = models.ImageField(verbose_name=_('image'), upload_to=type_new_path, null=True,
                              help_text="Imagen del tipo de novedad")
    info = jsonfield.JSONField(default=dict)
    template = jsonfield.JSONField(default=dict)
    is_active = models.BooleanField(default=True)


