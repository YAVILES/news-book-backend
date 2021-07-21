import uuid

from django.contrib.auth.models import User
from django.db import models
import jsonfield
from django_tenants.models import TenantMixin
from django.utils.translation import ugettext_lazy as _

# Create your models here.

ACTIVE = 1
INACTIVE = 0


class ModelBase(TenantMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    created = models.DateTimeField(verbose_name=_('created'), auto_now_add=True)
    updated = models.DateTimeField(verbose_name=_('updated'), auto_now=True)

    class Meta:
        abstract = True


class TypePerson(ModelBase):
    description = models.CharField(max_length=255, verbose_name="code", unique=True,
                                   help_text="Descripción del Tipo de Persona")
    priority = models.CharField(max_length=255, verbose_name="code", help_text="Prioridad del tipo de persona")
    status = models.SmallIntegerField(default=ACTIVE, choices=(
        (ACTIVE, _('activo')),
        (INACTIVE, _('inactivo'))
    ))


class Person(ModelBase):
    code = models.CharField(max_length=255, verbose_name="code", unique=True, help_text="Código de la persona")
    name = models.CharField(max_length=255, verbose_name="name", help_text="Nombre de la persona")
    last_name = models.CharField(max_length=255, verbose_name="lastname", help_text="Apellido de la persona")
    doc_ident = models.CharField(max_length=255, verbose_name="doc_ident", unique=True,
                                 help_text="Dpcumento de Identidad de la persona")
    address = models.CharField(max_length=255, verbose_name="address", help_text="Dirección de la persona")
    phone = models.CharField(max_length=255, verbose_name="phone", help_text="Teléfono de la persona")
    mobile = models.CharField(max_length=255, verbose_name="mobile", help_text="Número de celular de la persona")
    type_person = models.ForeignKey('TypePerson', verbose_name=_('type_person'), on_delete=models.PROTECT,
                                    help_text="tipo de persona")
    status = models.SmallIntegerField(default=ACTIVE, choices=(
        (ACTIVE, _('activo')),
        (INACTIVE, _('inactivo'))
    ))


class ClassificationNews(ModelBase):
    description = models.CharField(max_length=255, verbose_name="description", unique=True,
                                   help_text="Descripción de la clasificacion de novedad")
    priority = models.CharField(max_length=255, verbose_name="priority",
                                help_text="Prioridad de la clasificacion de novedad")
    status = models.SmallIntegerField(default=ACTIVE, choices=(
        (ACTIVE, _('activo')),
        (INACTIVE, _('inactivo'))
    ))


def type_new_path(type_news: 'TypeNews', file_name):
    return 'img/type_news/{0}/{1}'.format(type_news.description, file_name)


class TypeNews(ModelBase):
    description = models.CharField(max_length=255, verbose_name="description", unique=True,
                                   help_text="Descripción del tipo de novedad")
    classification_news = models.ForeignKey('ClassificationNews', verbose_name=_('classification_news'),
                                            on_delete=models.PROTECT, help_text="Clasificación del tipo de novedad")
    template = models.CharField(max_length=255, verbose_name="template", help_text="Plantilla del tipo de novedad")
    image = models.ImageField(verbose_name=_('image'), upload_to=type_new_path, null=True,
                              help_text="Imagen del tipo de novedad")
    info = jsonfield.JSONField(default=dict)
    status = models.SmallIntegerField(default=ACTIVE, choices=(
        (ACTIVE, _('activo')),
        (INACTIVE, _('inactivo'))
    ))


class Vehicle(ModelBase):
    license_plate = models.CharField(max_length=255, verbose_name="license_plate", unique=True,
                                     help_text="Placa del vehiculo")
    status = models.SmallIntegerField(default=ACTIVE, choices=(
        (ACTIVE, _('activo')),
        (INACTIVE, _('inactivo'))
    ))


class Material(ModelBase):
    code = models.CharField(max_length=255, verbose_name="code", unique=True, help_text="Código del material")
    serial = models.CharField(max_length=255, verbose_name="serial", unique=True, help_text="Serial del material")
    description = models.CharField(max_length=255, verbose_name="description", unique=True,
                                   help_text="Descripción del material")
    status = models.SmallIntegerField(default=ACTIVE, choices=(
        (ACTIVE, _('activo')),
        (INACTIVE, _('inactivo'))
    ))


class Schedule(ModelBase):
    description = models.CharField(max_length=255, verbose_name="description", unique=True,
                                   help_text="Descripción del horario")
    start_time = models.TimeField(null=False, help_text="Hora Inicial"),
    final_hour = models.TimeField(null=False, help_text="Hora final"),
    status = models.SmallIntegerField(default=ACTIVE, choices=(
        (ACTIVE, _('activo')),
        (INACTIVE, _('inactivo'))
    ))


class MaterialNews(ModelBase):
    material = models.ForeignKey(Material, verbose_name=_('material'), on_delete=models.PROTECT)
    news = models.ForeignKey('core.News', verbose_name=_('news'), on_delete=models.PROTECT)


class VehicleNews(ModelBase):
    vehicle = models.ForeignKey(Vehicle, verbose_name=_('vehicle'), on_delete=models.PROTECT)
    news = models.ForeignKey('core.News', verbose_name=_('news'), on_delete=models.PROTECT)


class PersonNews(ModelBase):
    persons = models.ForeignKey(Person, verbose_name=_('persons'), on_delete=models.PROTECT)
    news = models.ForeignKey('core.News', verbose_name=_('news'), on_delete=models.PROTECT)


class News(ModelBase):
    type_news = models.ForeignKey('TypeNews', verbose_name=_('type_news'), on_delete=models.PROTECT,
                                  help_text="Tipo de la novedad")

    message = models.TextField(verbose_name=_('message'), help_text="Mensaje de la novedad")
    info = jsonfield.JSONField(default=dict)
    created_by = models.ForeignKey(User, verbose_name=_('created_by'), on_delete=models.PROTECT,
                                   help_text="Creado por")
    materials = models.ManyToManyField(Material, verbose_name=_('materials'), related_name='materials',
                                       through=MaterialNews)
    vehicles = models.ManyToManyField(Vehicle, verbose_name=_('vehicles'), related_name='vehicles',
                                      through=VehicleNews)
    people = models.ManyToManyField(Person, verbose_name=_('people'), related_name='people',
                                    through=PersonNews)
    employee = models.CharField(max_length=255, verbose_name="employee",
                                help_text="Ficha del trabajador que generó la novedad")
