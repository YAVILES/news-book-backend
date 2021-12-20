import uuid

from django.db import models
import jsonfield
from django_tenants.models import TenantMixin
from django.utils.translation import ugettext_lazy as _

# Create your models here.
TITLE = "TITLE"
FREE_TEXT = 'FREE_TEXT'
PLANNED_STAFF = "PLANNED_STAFF"
OESVICA_STAFF = "OESVICA_STAFF"
FORMER_GUARD = "FORMER_GUARD"
DATE = "DATE"
HOUR = "HOUR"
SUB_LINE = "SUB_LINE"  # Alcance asociada al cliente y Ubicación de Ibarti
AMOUNT = "AMOUNT"
POINT = "POINT"
ROUNDS = "ROUNDS"
TEXTBOX = "TEXTBOX"
SELECTION = "SELECTION"
VEHICLES = "VEHICLES"
VEHICLE = "VEHICLE"
PERSONS = "PERSONS"
PERSON = "PERSON"
ROUND = "ROUND"

CODES_TEMPLATES = (
    (TITLE, "TITULO"),
    (FREE_TEXT, "TEXTO LIBRE"),
    (PLANNED_STAFF, "PERSONAL PLANIFICADO"),
    (OESVICA_STAFF, "PERSONAL OESVICA"),
    (FORMER_GUARD, "PERSONAL DE GUARDIA ANTERIOR"),
    (DATE, "FECHA"),
    (HOUR, "HORA"),
    (SUB_LINE, "SUB LINEA"),
    (AMOUNT, "CANTIDAD"),
    (POINT, "PUNTO"),
    (TEXTBOX, "CAJA DE TEXTO"),
    (SELECTION, "SELECCIÓN"),
    (VEHICLES, "VEHíCULOS"),
    (VEHICLE, "VEHíCULO"),
    (PERSONS, "PERSONAS"),
    (PERSON, "PERSONA"),
    (ROUND, "RONDA"),
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
    image = models.ImageField(verbose_name=_('image'), upload_to=type_new_path, null=True,
                              help_text="Imagen del tipo de novedad")
    info = models.CharField(max_length=255)
    is_changing_of_the_guard = models.BooleanField(default=False)
    template = jsonfield.JSONField(default=list, null=True)
    is_active = models.BooleanField(default=True)


