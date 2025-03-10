from django.core.exceptions import ValidationError
from django.db import transaction
from django_restql.mixins import DynamicFieldsMixin
from rest_framework import serializers

from apps.core.models import TypeNews
from apps.customers.models import Client, Domain


class ClientSerializer(DynamicFieldsMixin, serializers.ModelSerializer):
    id = serializers.IntegerField(read_only=True)
    schema_name = serializers.CharField(max_length=100)
    name = serializers.CharField(max_length=100)
    paid_until = serializers.DateField()
    on_trial = serializers.BooleanField()
    type_news = serializers.PrimaryKeyRelatedField(
        queryset=TypeNews.objects.all(),
        many=True,
        required=False,
        help_text="Tupos de novedades"
    )

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
                email = validated_data.pop('email', None)
                paid_until = validated_data.pop('paid_until', None)
                on_trial = validated_data.pop('on_trial', None)
                type_news = validated_data.pop('type_news', None)
                schema_name = validated_data.pop('schema_name', None)

                if type_news:
                    instance.type_news.set(type_news)
                if name:
                    instance.name = name
                if email:
                    instance.email = email
                if paid_until:
                    instance.paid_until = paid_until
                if on_trial:
                    instance.on_trial = on_trial
                instance.save(update_fields=['name', 'email', 'paid_until', 'on_trial'])

                if email:
                    try:
                        code = 'admin@' + schema_name
                        user_admin = User.objects.get(code=code)
                        if user_admin:
                            user_admin.email = email
                            user_admin.save(update_fields=['email'])
                    except:
                        pass

                return instance
        except ValidationError as error:
            raise serializers.ValidationError(detail={"error": error.messages})

    class Meta:
        model = Client
        fields = ('id', 'name', 'paid_until', 'on_trial', 'created_on', 'email', 'auto_create_schema', 'schema_name',
                  'type_news',)


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


class ClientSimpleSerializer(DynamicFieldsMixin, serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    name = serializers.CharField(max_length=100)
