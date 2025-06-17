from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.db import models
from datetime import datetime
import json
import jsonfield
from django.db.models.signals import post_save
from django.utils.translation import ugettext_lazy as _
from django.utils.functional import cached_property

from apps.core.models import ModelBase
from sequences import get_next_value
from apps.setting.tasks import send_email


def get_auto_code_material():
    return get_next_value('code_material', initial_value=1000000)


class Material(ModelBase):
    code = models.CharField(max_length=255, verbose_name="code", unique=True, help_text="Código del material")
    serial = models.CharField(
        max_length=255, verbose_name="serial", help_text="Serial del material", null=True, blank=True
    )
    description = models.CharField(max_length=255, verbose_name="description", unique=True,
                                   help_text="Descripción del material")
    is_active = models.BooleanField(default=True)


class EquipmentTools(ModelBase):
    serial = models.CharField(max_length=255, verbose_name="serial", unique=True, help_text="Serial")
    description = models.CharField(max_length=255, verbose_name="description", null=True, help_text="Descripción")
    mark = models.CharField(max_length=255, verbose_name="mark", null=True, help_text="Marca")
    model = models.CharField(max_length=255, verbose_name="model", null=True, help_text="Modelo")
    color = models.CharField(max_length=255, verbose_name="color", null=True, help_text="Color")
    year = models.CharField(max_length=255, verbose_name="year", null=True, help_text="Año")
    license_plate = models.CharField(max_length=255, verbose_name="license_plate", null=True, help_text="Placa")
    is_active = models.BooleanField(default=True)


class Schedule(ModelBase):
    description = models.CharField(max_length=255, verbose_name="description", unique=True,
                                   help_text="Descripción del horario")
    start_time = models.TimeField(blank=True, null=True, help_text="Hora Inicial")
    final_hour = models.TimeField(blank=True, null=True, help_text="Hora final")
    is_active = models.BooleanField(default=True)


class MaterialNews(ModelBase):
    material = models.ForeignKey(Material, verbose_name=_('material'), blank=True, on_delete=models.PROTECT)
    news = models.ForeignKey('main.News', verbose_name=_('news'), blank=True, on_delete=models.PROTECT)


class Vehicle(ModelBase):
    license_plate = models.CharField(max_length=255, verbose_name="license_plate", unique=True,
                                     help_text="Placa del vehiculo")
    owner_full_name = models.CharField(max_length=255, verbose_name="owner full name", unique=True,
                                       help_text="Nombre y Apellido del propieatario del vehiculo", null=True)
    model = models.CharField(max_length=255, verbose_name="model", help_text="Modelo del vehiculo", null=True)
    is_active = models.BooleanField(default=True)


class VehicleNews(ModelBase):
    vehicle = models.ForeignKey(Vehicle, verbose_name=_('vehicle'), on_delete=models.PROTECT)
    news = models.ForeignKey('main.News', verbose_name=_('news'), on_delete=models.PROTECT)


class TypePerson(ModelBase):
    description = models.CharField(max_length=255, verbose_name="code", unique=True,
                                   help_text="Descripción del Tipo de Persona")
    priority = models.CharField(max_length=255, verbose_name="code", help_text="Prioridad del tipo de persona")
    is_active = models.BooleanField(default=True)
    is_institution = models.BooleanField(default=False)
    requires_company_data = models.BooleanField(default=False)
    requires_guide_number = models.BooleanField(default=False)

    # Deletes an type person
    def delete(self, using=None, keep_parents=False):
        models.signals.pre_delete.send(
            sender=self.__class__,
            instance=self,
            using=using
        )
        self.is_active = False
        self.save(update_fields=['is_active', ])
        models.signals.post_delete.send(
            sender=self.__class__,
            instance=self,
            using=using
        )


def get_auto_code_person():
    return get_next_value('code_person', initial_value=100000)


class Person(ModelBase):
    code = models.CharField(max_length=255, verbose_name="code", unique=True, help_text="Código de la persona")
    name = models.CharField(max_length=255, verbose_name="name", help_text="Nombre de la persona")
    last_name = models.CharField(max_length=255, verbose_name="lastname", help_text="Apellido de la persona")
    doc_ident = models.CharField(max_length=255, verbose_name="doc_ident", unique=True,
                                 help_text="Documento de Identidad de la persona")
    address = models.CharField(max_length=255, verbose_name="address", null=True, blank=True,
                               help_text="Dirección de la persona")
    phone = models.CharField(max_length=255, verbose_name="phone", help_text="Teléfono de la persona", null=True, blank=True)
    mobile = models.CharField(max_length=255, verbose_name="mobile", help_text="Número de celular de la persona", null=True, blank=True)
    type_person = models.ForeignKey('main.TypePerson', verbose_name=_('type_person'), on_delete=models.PROTECT,
                                    help_text="tipo de persona")
    company =  models.CharField(max_length=255, verbose_name="address", null=True, blank=True)
    rif = models.CharField(max_length=255, verbose_name="rif", null=True, blank=True)
    blacklist = models.BooleanField(default=False)
    blacklist_reason = models.CharField(max_length=500, verbose_name="blacklist reason", null=True, blank=True)
    is_active = models.BooleanField(default=True)
    default_visit_reason = models.CharField(max_length=255, verbose_name="Motivo de visita por defecto", null=True, blank=True)
    default_visit_location = models.CharField(max_length=500, verbose_name="Lugar de visita por defecto", null=True, blank=True)

    def get_full_name(self):
        return "{name} {last_name}".format(name=self.name, last_name=self.last_name)

    @cached_property
    def full_name(self):
        return self.get_full_name()


class PersonNews(ModelBase):
    persons = models.ForeignKey(Person, verbose_name=_('persons'), on_delete=models.PROTECT)
    news = models.ForeignKey('main.News', verbose_name=_('news'), on_delete=models.PROTECT)


def get_new_number():
    return get_next_value('order')


class News(ModelBase):
    number = models.PositiveIntegerField(
        verbose_name='Number', primary_key=False, db_index=True, default=get_new_number
    )
    type_news = models.ForeignKey('core.TypeNews', verbose_name=_('type_news'), on_delete=models.PROTECT,
                                  help_text="Tipo de la novedad", blank=True)
    template = jsonfield.JSONField(default=list)
    info = jsonfield.JSONField(default=dict)
    created_by = models.ForeignKey('security.User', verbose_name=_('created_by'), on_delete=models.PROTECT,
                                   help_text="Usuario por el que fue crada la novedad", null=True)
    materials = models.ManyToManyField(Material, verbose_name=_('materials'), related_name='news', through=MaterialNews)
    vehicles = models.ManyToManyField(Vehicle, verbose_name=_('vehicles'), related_name='news', through=VehicleNews)
    people = models.ManyToManyField(Person, verbose_name=_('people'), related_name='news', through=PersonNews)
    employee = models.CharField(max_length=255, verbose_name="employee",
                                help_text="Ficha del trabajador que generó la novedad")
    location = models.ForeignKey('Location', verbose_name=_('location'), on_delete=models.PROTECT,
                                 help_text="Ubicación o Libro donde se generó la novedad", null=True)

    @cached_property
    def contains_attached_files(self):
        try:
            if not self.info:  # Si info está vacío
                return False

            info_data = self.info if isinstance(self.info, dict) else json.loads(self.info)
            for key, value in info_data.items():
                if key.startswith('ATTACHED_FILE_'):
                    attached_files = value.get('attachedFiles')
                    # Verifica si attachedFiles tiene contenido
                    if attached_files and ((isinstance(attached_files, (list, dict)) and attached_files) or
                                           (isinstance(attached_files, str) and attached_files.strip())):
                            return True
            return False
        except (json.JSONDecodeError, AttributeError):
            return False

    class Meta:
        verbose_name = _('new')
        verbose_name_plural = _('news')


class Location(ModelBase):
    code = models.CharField(max_length=255, verbose_name=_('code'), null=False, blank=False)
    name = models.CharField(max_length=255, verbose_name=_('name'), unique=True, null=False, blank=False)
    phone1 = models.CharField(max_length=255, verbose_name=_('phone1'), blank=True, null=True)
    phone2 = models.CharField(max_length=255, verbose_name=_('phone2'), blank=True, null=True)
    is_active = models.BooleanField(default=True)


class Point(ModelBase):
    code = models.CharField(max_length=255, verbose_name=_('code'), unique=True, null=False, blank=False)
    name = models.CharField(max_length=255, verbose_name=_('name'), unique=True, null=False, blank=False)
    is_active = models.BooleanField(default=True)
