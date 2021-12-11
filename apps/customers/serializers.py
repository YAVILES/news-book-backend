from django_restql.mixins import DynamicFieldsMixin
from rest_framework import serializers

from apps.customers.models import Client, Domain


class ClientSerializer(DynamicFieldsMixin, serializers.Serializer):
    class Meta:
        model = Client
        fields = serializers.ALL_FIELDS


class DomainSerializer(DynamicFieldsMixin, serializers.Serializer):
    class Meta:
        model = Domain
        fields = serializers.ALL_FIELDS
