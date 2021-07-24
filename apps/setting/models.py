from django.contrib.auth.models import Group
from django.db import models
from django.utils.translation import ugettext_lazy as _

from apps.core.models import ModelBase, TypeNews
from apps.main.models import Schedule


class GroupNotification(ModelBase):
    group = models.ForeignKey(Group, verbose_name=_('group'), on_delete=models.PROTECT)
    notification = models.ForeignKey('setting.Notification', verbose_name=_('notification'), on_delete=models.PROTECT)


class Notification(ModelBase):
    RECURRENT = 0
    OBLIGATORY = 1
    description = models.CharField(max_length=255, verbose_name="description", unique=True,
                                   help_text="Descripción de la Notificación")
    type = models.SmallIntegerField(default=RECURRENT, verbose_name="type", choices=(
        (RECURRENT, _('Recurrente')),
        (OBLIGATORY, _('Obligatoria'))
    ))
    groups = models.ManyToManyField(Group, verbose_name=_('groups'), related_name='notifications',
                                    through=GroupNotification)
    schedule = models.ForeignKey(Schedule, verbose_name=_('schedule'), on_delete=models.PROTECT, null=True)
    type_news = models.ForeignKey(TypeNews, verbose_name=_('type_news'), on_delete=models.PROTECT)
    every_day = models.BooleanField(default=True)
    day = models.DateField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
