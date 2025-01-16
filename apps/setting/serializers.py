import datetime
import json

import pytz
from django.contrib.auth.models import Group
from django.core.exceptions import ObjectDoesNotExist
from django.db import connections
from django.utils.translation import ugettext_lazy as _
from django_celery_beat.models import PeriodicTask, CrontabSchedule, ClockedSchedule
from django_celery_results.models import TaskResult
from django_restql.mixins import DynamicFieldsMixin
from django_tenants.utils import get_tenant_database_alias
from django_tenants_celery_beat.models import PeriodicTaskTenantLink
from rest_framework import serializers

from apps.core.serializers import TypeNewsSimpleSerializer
from apps.customers.models import Client
from apps.main.models import Schedule
from apps.main.serializers import ScheduleDefaultSerializer
from apps.security.serializers import RoleDefaultSerializer
from apps.setting.models import Notification


class NotificationDefaultSerializer(DynamicFieldsMixin, serializers.ModelSerializer):
    day = serializers.DateField(required=False, default=None, allow_null=True)
    type_display = serializers.CharField(source='get_type_display', read_only=True)
    groups = serializers.PrimaryKeyRelatedField(queryset=Group.objects.all(), many=True, write_only=True)
    groups_display = RoleDefaultSerializer(source="groups", many=True, read_only=True)
    schedule = serializers.PrimaryKeyRelatedField(queryset=Schedule.objects.all(), many=True, required=False)
    schedule_display = ScheduleDefaultSerializer(source="schedule", many=True, read_only=True)
    days = serializers.ListField(child=serializers.DateField(), required=False)
    week_days = serializers.ListField(child=serializers.IntegerField(), required=False)
    type_news_display = TypeNewsSimpleSerializer(read_only=True, source="type_news")
    periodic_tasks = serializers.ListField(child=serializers.IntegerField(), required=False)

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

    def create(self, validated_data):
        request = self.context.get('request')
        instance: Notification = super(NotificationDefaultSerializer, self).create(validated_data)
        type_notif = instance.type
        frequency = instance.frequency
        schedules = validated_data.get('schedule')
        periodic_tasks_pre = instance.periodic_tasks
        description = instance.description
        day = instance.day
        days = instance.days
        week_days = instance.week_days
        connection = connections[get_tenant_database_alias()]
        public_tenant = Client.objects.get(schema_name="public")
        connection.set_tenant(public_tenant, True)
        if periodic_tasks_pre:
            PeriodicTask.objects.filter(id__in=periodic_tasks_pre).delete()

        periodic_tasks = []
        if instance.is_active:
            if type_notif == Notification.OBLIGATORY:
                if frequency == Notification.EVERY_DAY:
                    for schedule in schedules:
                        minute = schedule.final_hour.minute
                        hour = schedule.final_hour.hour
                        name_task = "{0} {1} {2}".format(
                            description,
                            schedule.description,
                            datetime.datetime.now()
                        )
                        crontab_schedule, _ = CrontabSchedule.objects.get_or_create(
                            minute=minute,
                            hour=hour,
                            day_of_week='*',
                            day_of_month='*',
                            month_of_year='*',
                            timezone=pytz.timezone('America/Caracas')
                        )
                        periodicTask = PeriodicTask.objects.create(
                            crontab=crontab_schedule,
                            args=json.dumps([str(instance.id)]),
                            name=name_task,
                            task='apps.setting.tasks.generate_notification_not_fulfilled',
                            start_time=datetime.datetime.now()
                        )
                        tl = PeriodicTaskTenantLink(
                            tenant=request.tenant,
                            periodic_task=periodicTask,
                            use_tenant_timezone=True
                        )
                        tl.save(update_fields=[])
                        periodic_tasks.append(str(periodicTask.id))
                elif frequency == Notification.JUST_ONE_DAY:
                    for schedule in schedules:
                        name_task = "{0} {1} {2}".format(
                            description,
                            schedule.description,
                            datetime.datetime.now()
                        )
                        clocked_schedule, _ = ClockedSchedule.objects.get_or_create(
                            clocked_time=schedule.final_hour
                        )
                        periodicTask = PeriodicTask.objects.create(
                            clocked=clocked_schedule,
                            args=json.dumps([str(instance.id)]),
                            name=name_task,
                            task='apps.setting.tasks.generate_notification_not_fulfilled',
                            start_time=day,
                            one_off=True
                        )
                        tl = PeriodicTaskTenantLink(
                            tenant=request.tenant,
                            periodic_task=periodicTask,
                            use_tenant_timezone=True
                        )
                        tl.save(update_fields=[])
                        periodic_tasks.append(str(periodicTask.id))
                elif frequency == Notification.MORE_THAN_ONE_DAY:
                    for day in days:
                        for schedule in schedules:
                            name_task = "{0} {1} {2}".format(
                                description,
                                schedule.description,
                                datetime.datetime.now()
                            )
                            clocked_schedule, _ = ClockedSchedule.objects.get_or_create(
                                clocked_time=schedule.final_hour
                            )
                            periodicTask = PeriodicTask.objects.create(
                                clocked=clocked_schedule,
                                args=json.dumps([str(instance.id)]),
                                name=name_task,
                                task='apps.setting.tasks.generate_notification_not_fulfilled',
                                start_time=day,
                                one_off=True
                            )
                            tl = PeriodicTaskTenantLink(
                                tenant=request.tenant,
                                periodic_task=periodicTask,
                                use_tenant_timezone=True
                            )
                            tl.save(update_fields=[])
                            periodic_tasks.append(str(periodicTask.id))
                elif frequency == Notification.BY_DAY_DAYS:
                    days = ""
                    for day in week_days:
                        if day == "":
                            days += str(day)
                        else:
                            days += ", " + str(day)

                    for schedule in schedules:
                        minute = schedule.final_hour.minute
                        hour = schedule.final_hour.hour
                        name_task = "{0} {1} {2}".format(
                            description,
                            schedule.description,
                            datetime.datetime.now()
                        )
                        crontab_schedule, _ = CrontabSchedule.objects.get_or_create(
                            minute=minute,
                            hour=hour,
                            day_of_week=days,
                            day_of_month='*',
                            month_of_year='*',
                            timezone=pytz.timezone('America/Caracas')
                        )
                        periodicTask = PeriodicTask.objects.create(
                            crontab=crontab_schedule,
                            args=json.dumps([str(instance.id)]),
                            name=name_task,
                            task='apps.setting.tasks.generate_notification_not_fulfilled',
                            start_time=day,
                            one_off=True
                        )
                        tl = PeriodicTaskTenantLink(
                            tenant=request.tenant,
                            periodic_task=periodicTask,
                            use_tenant_timezone=True
                        )
                        tl.save(update_fields=[])
                        periodic_tasks.append(str(periodicTask.id))

        connection.set_tenant(request.tenant, True)
        instance.periodic_tasks = periodic_tasks
        instance.save(update_fields=['periodic_tasks'])
        return instance

    def update(self, instance, validated_data):
        request = self.context.get('request')
        instance = super(NotificationDefaultSerializer, self).update(instance, validated_data)
        type_notif = instance.type
        frequency = instance.frequency
        schedules = validated_data.get('schedule')
        periodic_tasks_pre = instance.periodic_tasks
        description = instance.description
        day = instance.day
        days = instance.days
        week_days = instance.week_days
        connection = connections[get_tenant_database_alias()]
        public_tenant = Client.objects.get(schema_name="public")
        connection.set_tenant(public_tenant, True)
        if periodic_tasks_pre:
            PeriodicTask.objects.filter(id__in=periodic_tasks_pre).delete()

        periodic_tasks = []
        if instance.is_active:
            if type_notif == Notification.OBLIGATORY:
                if frequency == Notification.EVERY_DAY:
                    for schedule in schedules:
                        minute = schedule.final_hour.minute
                        hour = schedule.final_hour.hour
                        name_task = "{0} {1} {2}".format(
                            description,
                            schedule.description,
                            datetime.datetime.now()
                        )
                        crontab_schedule, _ = CrontabSchedule.objects.get_or_create(
                            minute=minute,
                            hour=hour,
                            day_of_week='*',
                            day_of_month='*',
                            month_of_year='*',
                            timezone=pytz.timezone('America/Caracas')
                        )
                        periodicTask = PeriodicTask.objects.create(
                            crontab=crontab_schedule,
                            args=json.dumps([str(instance.id)]),
                            name=name_task,
                            task='apps.setting.tasks.generate_notification_not_fulfilled',
                            start_time=datetime.datetime.now()
                        )
                        tl = PeriodicTaskTenantLink(
                            tenant=request.tenant,
                            periodic_task=periodicTask,
                            use_tenant_timezone=True
                        )
                        tl.save(update_fields=[])
                        periodic_tasks.append(str(periodicTask.id))
                elif frequency == Notification.JUST_ONE_DAY:
                    for schedule in schedules:
                        name_task = "{0} {1} {2}".format(
                            description,
                            schedule.description,
                            datetime.datetime.now()
                        )
                        clocked_schedule, _ = ClockedSchedule.objects.get_or_create(
                            clocked_time=schedule.final_hour
                        )
                        periodicTask = PeriodicTask.objects.create(
                            clocked=clocked_schedule,
                            args=json.dumps([str(instance.id)]),
                            name=name_task,
                            task='apps.setting.tasks.generate_notification_not_fulfilled',
                            start_time=day,
                            one_off=True
                        )
                        tl = PeriodicTaskTenantLink(
                            tenant=request.tenant,
                            periodic_task=periodicTask,
                            use_tenant_timezone=True
                        )
                        tl.save(update_fields=[])
                        periodic_tasks.append(str(periodicTask.id))
                elif frequency == Notification.MORE_THAN_ONE_DAY:
                    for day in days:
                        for schedule in schedules:
                            name_task = "{0} {1} {2}".format(
                                description,
                                schedule.description,
                                datetime.datetime.now()
                            )
                            clocked_schedule, _ = ClockedSchedule.objects.get_or_create(
                                clocked_time=schedule.final_hour
                            )
                            periodicTask = PeriodicTask.objects.create(
                                clocked=clocked_schedule,
                                args=json.dumps([str(instance.id)]),
                                name=name_task,
                                task='apps.setting.tasks.generate_notification_not_fulfilled',
                                start_time=day,
                                one_off=True
                            )
                            tl = PeriodicTaskTenantLink(
                                tenant=request.tenant,
                                periodic_task=periodicTask,
                                use_tenant_timezone=True
                            )
                            tl.save(update_fields=[])
                            periodic_tasks.append(str(periodicTask.id))
                elif frequency == Notification.BY_DAY_DAYS:
                    days = ""
                    for day in week_days:
                        if day == "":
                            days += str(day)
                        else:
                            days += ", " + str(day)

                    for schedule in schedules:
                        minute = schedule.final_hour.minute
                        hour = schedule.final_hour.hour
                        name_task = "{0} {1} {2}".format(
                            description,
                            schedule.description,
                            datetime.datetime.now()
                        )
                        crontab_schedule, _ = CrontabSchedule.objects.get_or_create(
                            minute=minute,
                            hour=hour,
                            day_of_week=days,
                            day_of_month='*',
                            month_of_year='*',
                            timezone=pytz.timezone('America/Caracas')
                        )
                        periodicTask = PeriodicTask.objects.create(
                            crontab=crontab_schedule,
                            args=json.dumps([str(instance.id)]),
                            name=name_task,
                            task='apps.setting.tasks.generate_notification_not_fulfilled',
                            start_time=day,
                            one_off=True
                        )
                        tl = PeriodicTaskTenantLink(
                            tenant=request.tenant,
                            periodic_task=periodicTask,
                            use_tenant_timezone=True
                        )
                        tl.save(update_fields=[])
                        periodic_tasks.append(str(periodicTask.id))

        connection.set_tenant(request.tenant, True)
        instance.periodic_tasks = periodic_tasks
        instance.save(update_fields=['periodic_tasks'])
        return instance

    class Meta:
        model = Notification
        exclude = ('updated',)


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
