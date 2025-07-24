from django.contrib.auth.models import Group
from django.db import models
from django.utils.translation import ugettext_lazy as _

from apps.core.models import ModelBase, TypeNews
from apps.main.models import Schedule, Location
from django.contrib.postgres.fields import ArrayField

MONDAY = 0
TUESDAY = 1
WEDNESDAY = 2
THURSDAY = 3
FRIDAY = 4
SATURDAY = 5
SUNDAY = 6

DAYS = (
    (MONDAY, _('Lunes')),
    (TUESDAY, _('Martes')),
    (WEDNESDAY, _('Miercoles')),
    (THURSDAY, _('Jueves')),
    (FRIDAY, _('Viernes')),
    (SATURDAY, _('Sábado')),
    (SUNDAY, _('Domingo')),
)


class ScheduleNotification(ModelBase):
    schedule = models.ForeignKey(Schedule, verbose_name=_('schedule'), on_delete=models.PROTECT)
    notification = models.ForeignKey('setting.Notification', verbose_name=_('notification'), on_delete=models.PROTECT)


class GroupNotification(ModelBase):
    group = models.ForeignKey(Group, verbose_name=_('group'), on_delete=models.PROTECT)
    notification = models.ForeignKey('setting.Notification', verbose_name=_('notification'), on_delete=models.PROTECT)


class Notification(ModelBase):
    RECURRENT = 0
    OBLIGATORY = 1
    EVERY_DAY = 1
    JUST_ONE_DAY = 2
    MORE_THAN_ONE_DAY = 3
    BY_DAY_DAYS = 4
    FREQUENCIES = (
        (EVERY_DAY, _('Todos los días')),
        (JUST_ONE_DAY, _('Solo un día')),
        (MORE_THAN_ONE_DAY, _('Mas de un día')),
        (BY_DAY_DAYS, _('días por semana')),
    )
    description = models.CharField(max_length=255, verbose_name="description", unique=True,
                                   help_text="Descripción de la Notificación")
    type = models.SmallIntegerField(default=RECURRENT, verbose_name="type", choices=(
        (RECURRENT, _('Recurrente')),
        (OBLIGATORY, _('Obligatoria'))
    ))
    groups = models.ManyToManyField(Group, verbose_name=_('groups'), related_name='notifications',
                                    through=GroupNotification)
    schedule = models.ManyToManyField(Schedule, verbose_name=_('schedule'), related_name='notifications',
                                      through=ScheduleNotification)
    type_news = models.ForeignKey(TypeNews, verbose_name=_('type_news'), on_delete=models.PROTECT)
    frequency = models.SmallIntegerField(default=EVERY_DAY, verbose_name="frequency", choices=FREQUENCIES)
    day = models.DateField(blank=True, null=True, verbose_name="day")
    days = ArrayField(
        models.DateField(),
        default=list,
        null=True,
        verbose_name=_('days'),
    )
    week_days = ArrayField(
        models.SmallIntegerField(),
        default=list,
        null=True,
        verbose_name=_('week days'),
        size=7
    )
    is_active = models.BooleanField(default=True)
    periodic_tasks = ArrayField(
        models.CharField(max_length=255),
        size=255,
        default=list,
        null=True,
        verbose_name=_('periodic tasks ids'),
    )

    def __str__(self):
        return "{description}".format(description=self.description)


class FacialRecognitionEvent(models.Model):
    IN = "IN"
    OUT = "OUT"

    user_id = models.CharField(max_length=100)
    event_time = models.DateTimeField()
    raw_data = models.JSONField()
    movement_type = models.CharField(default=IN, max_length=3, verbose_name="movement_type", choices=(
        (IN, _('Entrada')),
        (OUT, _('Salida'))
    ))
    location = models.ForeignKey(Location, verbose_name=_('location'), on_delete=models.PROTECT,
                                 help_text="Ubicación o Libro donde se generó el reconocimiento", null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['user_id']),
            models.Index(fields=['event_time']),
        ]
        ordering = ['-event_time']

    def __str__(self):
        return f"{self.user_id} - {self.event_time}"