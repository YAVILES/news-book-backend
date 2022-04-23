import datetime
import json

import pytz
from django.contrib.auth.models import Group
from django.core.exceptions import ObjectDoesNotExist
from django.db import models
from django.db.models.signals import post_save
from django.utils.translation import ugettext_lazy as _
from django_celery_beat.models import IntervalSchedule, PeriodicTask, CrontabSchedule

from apps.core.models import ModelBase, TypeNews
from apps.main.models import Schedule
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
    periodic_tasks = models.ManyToManyField(PeriodicTask, verbose_name=_('periodic tasks'), related_name='tasks')

    def __str__(self):
        return "{description}".format(description=self.description)


def post_save_new(sender, instance: Notification, **kwargs):
    if isinstance(instance, Notification) and instance.type == Notification.OBLIGATORY:
        try:
            instance.periodic_tasks.all().delete()
            periodic_tasks = []
            if instance.frequency == Notification.EVERY_DAY:
                for schedule in instance.schedule.all():
                    if instance.frequency == Notification.EVERY_DAY:
                        crontab_schedule, _ = CrontabSchedule.objects.get_or_create(
                            minute=schedule.final_hour.minute,
                            hour=schedule.final_hour.hour,
                            day_of_week='*',
                            day_of_month='*',
                            month_of_year='*',
                            timezone=pytz.timezone('America/Caracas')
                        )
                        try:
                            periodicTask = PeriodicTask.objects.get(
                                name="{0} {1} {2}".format(instance.description, instance.type_news.description,
                                                          schedule.description),
                                task='apps.setting.tasks.generate_notification_not_fulfilled'
                            )
                            periodicTask.crontab = crontab_schedule
                            periodicTask.save(update_fields=['crontab'])
                        except ObjectDoesNotExist:
                            periodicTask = PeriodicTask.objects.create(
                                crontab=crontab_schedule,
                                args=json.dumps([str(instance.id)]),
                                name="{0} {1} {2}".format(instance.description, instance.type_news.description,
                                                          schedule.description),
                                task='apps.setting.tasks.generate_notification_not_fulfilled'
                            )
                        periodic_tasks.append(periodicTask)
                    elif instance.frequency == Notification.JUST_ONE_DAY:
                        pass
                    elif instance.frequency == Notification.MORE_THAN_ONE_DAY:
                        pass
                    elif instance.frequency == Notification.BY_DAY_DAYS:
                        pass
            instance.periodic_tasks.set(periodic_tasks)
        except Exception as e:
            print(e.__str__())
            pass


post_save.connect(post_save_new, sender=Notification)
