from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.db import models
import jsonfield
from django.db.models.signals import post_save
from django.utils.translation import ugettext_lazy as _

from apps.core.models import ModelBase
from sequences import get_next_value


class Material(ModelBase):
    code = models.CharField(max_length=255, verbose_name="code", unique=True, help_text="Código del material")
    serial = models.CharField(max_length=255, verbose_name="serial", unique=True, help_text="Serial del material")
    description = models.CharField(max_length=255, verbose_name="description", unique=True,
                                   help_text="Descripción del material")
    is_active = models.BooleanField(default=True)


class EquipmentTools(ModelBase):
    serial = models.CharField(max_length=255, verbose_name="serial", unique=True, help_text="Serial")
    description = models.CharField(max_length=255, verbose_name="description", null=True, help_text="Descripción")
    mark = models.CharField(max_length=255, verbose_name="mark", null=True, help_text="Marca")
    model = models.CharField(max_length=255, verbose_name="model", null=True,  help_text="Modelo")
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
    is_active = models.BooleanField(default=True)


class VehicleNews(ModelBase):
    vehicle = models.ForeignKey(Vehicle, verbose_name=_('vehicle'), on_delete=models.PROTECT)
    news = models.ForeignKey('main.News', verbose_name=_('news'), on_delete=models.PROTECT)


class TypePerson(ModelBase):
    description = models.CharField(max_length=255, verbose_name="code", unique=True,
                                   help_text="Descripción del Tipo de Persona")
    priority = models.CharField( max_length=255, verbose_name="code", help_text="Prioridad del tipo de persona")
    is_active = models.BooleanField(default=True)

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


class Person(ModelBase):
    code = models.CharField(max_length=255, verbose_name="code", unique=True, help_text="Código de la persona")
    name = models.CharField(max_length=255, verbose_name="name", help_text="Nombre de la persona")
    last_name = models.CharField(max_length=255, verbose_name="lastname", help_text="Apellido de la persona")
    doc_ident = models.CharField(max_length=255, verbose_name="doc_ident", unique=True,
                                 help_text="Documento de Identidad de la persona")
    address = models.CharField( max_length=255, verbose_name="address", help_text="Dirección de la persona")
    phone = models.CharField(max_length=255, verbose_name="phone", help_text="Teléfono de la persona")
    mobile = models.CharField(max_length=255, verbose_name="mobile", help_text="Número de celular de la persona")
    type_person = models.ForeignKey('main.TypePerson', verbose_name=_('type_person'), on_delete=models.PROTECT,
                                    help_text="tipo de persona")
    is_active = models.BooleanField(default=True)


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
                                   help_text="Usuario por el que fue crada la novedad",  null=True)
    materials = models.ManyToManyField(Material, verbose_name=_('materials'), related_name='news', through=MaterialNews)
    vehicles = models.ManyToManyField(Vehicle, verbose_name=_('vehicles'), related_name='news', through=VehicleNews)
    people = models.ManyToManyField(Person, verbose_name=_('people'), related_name='news', through=PersonNews)
    employee = models.CharField(max_length=255, verbose_name="employee",
                                help_text="Ficha del trabajador que generó la novedad")
    location = models.ForeignKey('Location', verbose_name=_('location'), on_delete=models.PROTECT,
                                 help_text="Ubicación o Libro donde se generó la novedad", null=True)

    class Meta:
        verbose_name = _('new')
        verbose_name_plural = _('news')


class Location(ModelBase):
    code = models.CharField(max_length=255, verbose_name=_('code'), unique=True, null=False, blank=False)
    name = models.CharField(max_length=255, verbose_name=_('name'), unique=True, null=False, blank=False)
    phone1 = models.CharField(max_length=255, verbose_name=_('phone1'), blank=True, null=True)
    phone2 = models.CharField(max_length=255, verbose_name=_('phone2'), blank=True, null=True)
    is_active = models.BooleanField(default=True)


class Point(ModelBase):
    code = models.CharField(max_length=255, verbose_name=_('code'), unique=True, null=False, blank=False)
    name = models.CharField(max_length=255, verbose_name=_('name'), unique=True, null=False, blank=False)
    is_active = models.BooleanField(default=True)


#    SIGNALS
def post_save_client(sender, instance: News, **kwargs):
    from apps.security.models import User
    if isinstance(instance, News) and not kwargs['created']:
        try:
            emails = User.objects.filter(
                is_active=True, email__isnull=False).values_list('email', flat=True)
            email = EmailMultiAlternatives(
                instance.type_news.description,
                'TEST EMAIL',
                settings.EMAIL_HOST_USER,
                emails
            )
            # email.attach_alternative(content, 'text/html')
            try:
                email.send()
            except ValueError as e:
                pass
        except:
            pass


post_save.connect(post_save_client, sender=News)
