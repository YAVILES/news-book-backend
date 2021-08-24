from django.contrib.auth.models import Group
from django_restql.mixins import DynamicFieldsMixin
from rest_framework import serializers

from apps.main.models import Schedule
from apps.setting.models import Notification


class NotificationDefaultSerializer(DynamicFieldsMixin, serializers.ModelSerializer):
    day = serializers.DateField(required=False, default=None)
    type_display = serializers.CharField(
        source='get_type_display', read_only=True)
    groups = serializers.PrimaryKeyRelatedField(
        queryset=Group.objects.all(), many=True)
    schedule = serializers.PrimaryKeyRelatedField(
        queryset=Schedule.objects.all(), many=True)
    days = serializers.ListField(child=serializers.DateField(), required=False)

    class Meta:
        model = Notification
        fields = serializers.ALL_FIELDS
