from django.contrib.auth.models import Group
from django.core.exceptions import ObjectDoesNotExist
from django.utils.translation import ugettext_lazy as _
from django_celery_beat.models import PeriodicTask, CrontabSchedule
from django_celery_results.models import TaskResult
from django_restql.mixins import DynamicFieldsMixin
from rest_framework import serializers

from apps.main.models import Schedule
from apps.main.serializers import ScheduleDefaultSerializer
from apps.security.serializers import RoleDefaultSerializer
from apps.setting.models import Notification


class NotificationDefaultSerializer(DynamicFieldsMixin, serializers.ModelSerializer):
    day = serializers.DateField(required=False, default=None, allow_null=True)
    type_display = serializers.CharField(source='get_type_display', read_only=True)
    groups = serializers.PrimaryKeyRelatedField(queryset=Group.objects.all(), many=True, write_only=True)
    groups_display = RoleDefaultSerializer(source="groups", many=True, read_only=True)
    schedule = serializers.PrimaryKeyRelatedField(queryset=Schedule.objects.all(), many=True, required=False,
                                                  write_only=True)
    schedule_display = ScheduleDefaultSerializer(source="schedule", many=True, read_only=True)
    days = serializers.ListField(child=serializers.DateField(), required=False)
    week_days = serializers.ListField(child=serializers.IntegerField(), required=False)

    def validate(self, attrs):
        days = attrs.get('days', None)
        day = attrs.get('day', None)
        week_days = attrs.get('week_days', None)
        frequency = attrs.get('frequency', None)
        _type = attrs.get('type', None)
        schedule = attrs.get('schedule', [])
        if _type == Notification.OBLIGATORY:
            if not schedule:
                raise serializers.ValidationError(detail={
                    "error": _("Para una notificación obligatoria se necesita al menos un horario")
                })
            if frequency == Notification.JUST_ONE_DAY and not day:
                raise serializers.ValidationError(detail={"error": _("El día es obligatorio")})
            if frequency == Notification.MORE_THAN_ONE_DAY and not days:
                raise serializers.ValidationError(detail={"error": _("Debe agregar al menos un día")})
            if frequency == Notification.BY_DAY_DAYS and not week_days:
                raise serializers.ValidationError(detail={"error": _("Debe agregar al menos un día de la semana")})
        return attrs

    class Meta:
        model = Notification
        exclude = ('periodic_tasks',)


class TaskResultDefaultSerializer(DynamicFieldsMixin, serializers.ModelSerializer):
    module = serializers.SerializerMethodField(read_only=True)

    def get_module(self, task: TaskResult):
        try:
            return PeriodicTask.objects.get(task=task.task_name).name
        except ObjectDoesNotExist:
            return None

    class Meta:
        model = TaskResult
        fields = serializers.ALL_FIELDS


class CrontabDefaultSerializer(DynamicFieldsMixin, serializers.ModelSerializer):
    class Meta:
        model = CrontabSchedule
        exclude = ('timezone',)


class PeriodicTaskDefaultSerializer(DynamicFieldsMixin, serializers.ModelSerializer):
    crontab_display = CrontabDefaultSerializer(read_only=True, source="crontab")

    class Meta:
        model = PeriodicTask
        fields = serializers.ALL_FIELDS
