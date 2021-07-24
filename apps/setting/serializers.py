from django_restql.mixins import DynamicFieldsMixin
from rest_framework import serializers

from apps.setting.models import Notification


class NotificationDefaultSerializer(DynamicFieldsMixin, serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = serializers.ALL_FIELDS
