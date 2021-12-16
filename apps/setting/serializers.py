from django.contrib.auth.models import Group
from django.utils.translation import ugettext_lazy as _
from django_restql.mixins import DynamicFieldsMixin
from rest_framework import serializers

from apps.main.models import Schedule
from apps.setting.models import Notification


class NotificationDefaultSerializer(DynamicFieldsMixin, serializers.ModelSerializer):
    day = serializers.DateField(required=False, default=None, allow_null=True)
    type_display = serializers.CharField(source='get_type_display', read_only=True)
    groups = serializers.PrimaryKeyRelatedField(queryset=Group.objects.all(), many=True)
    groups_display = serializers.SerializerMethodField(read_only=True)
    schedule = serializers.PrimaryKeyRelatedField(queryset=Schedule.objects.all(), many=True)
    days = serializers.ListField(child=serializers.DateField(), required=False)
    week_days = serializers.ListField(child=serializers.IntegerField(), required=False)

    def get_groups_display(self, attr: Notification):
        groups_display = []
        for group_name in attr.groups.all().values_list('name', flat=True):
            groups_display.append(group_name)
        return groups_display

    def validate(self, attrs):
        days = attrs.get('days', None)
        day = attrs.get('day', None)
        if day == "":
            attrs.set('day', None)
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
        fields = serializers.ALL_FIELDS
