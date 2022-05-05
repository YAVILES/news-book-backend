from django.core.exceptions import ValidationError
from django.db import transaction
from django_restql.mixins import DynamicFieldsMixin
from rest_framework import serializers

from apps.customers.models import Client, Domain


class ClientSerializer(DynamicFieldsMixin, serializers.ModelSerializer):
    id = serializers.IntegerField(read_only=True)
    schema_name = serializers.CharField(max_length=100)
    name = serializers.CharField(max_length=100)
    paid_until = serializers.DateField()
    on_trial = serializers.BooleanField()

    def create(self, validated_data):
        try:
            with transaction.atomic():
                tenant = Client(**validated_data)
                tenant.save()
                return tenant
        except ValidationError as error:
            raise serializers.ValidationError(detail={"error": error.detail})

    def update(self, instance: Domain, validated_data):
        try:
            with transaction.atomic():
                name = validated_data.pop('name', None)
                paid_until = validated_data.pop('paid_until', None)
                on_trial = validated_data.pop('on_trial', None)
                if name:
                    instance.name = name
                if paid_until:
                    instance.paid_until = paid_until
                if on_trial:
                    instance.on_trial = on_trial
                instance.save(update_fields=['name', 'paid_until', 'on_trial'])
                
                return instance
        except ValidationError as error:
            raise serializers.ValidationError(detail={"error": error.messages})

        return instance

    class Meta:
        model = Client
        fields = serializers.ALL_FIELDS


class DomainSerializer(DynamicFieldsMixin, serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    domain = serializers.CharField(required=False)
    tenant = ClientSerializer(read_only=True)
    tenant_id = serializers.IntegerField()

    def create(self, validated_data):
        try:
            with transaction.atomic():
                domain = Domain.objects.create(
                    **validated_data
                )
                return domain
        except ValidationError as error:
            raise serializers.ValidationError(detail={"error": error.detail})

    def update(self, instance: Domain, validated_data):
        try:
            with transaction.atomic():
                domain = validated_data.pop('domain', None)
                tenant_id = validated_data.pop('tenant_id', None)
                instance.tenant_id = tenant_id
                instance.domain = domain
                instance.save(update_fields=['domain', 'tenant_id'])
                return instance
        except ValidationError as error:
            raise serializers.ValidationError(detail={"error": error.messages})

        return instance

    class Meta:
        model = Domain
        fields = serializers.ALL_FIELDS
