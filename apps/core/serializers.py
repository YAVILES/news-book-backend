# coding=utf-8
from django_restql.mixins import DynamicFieldsMixin
from rest_framework import serializers
from django.db import transaction
from apps.core.models import TypeNews


class TypeNewsDefaultSerializer(DynamicFieldsMixin, serializers.ModelSerializer):
    info = serializers.CharField(required=False)
    template = serializers.JSONField(required=False, default=list)

    image_display = serializers.SerializerMethodField(read_only=True)

    def get_image_display(self, obj: 'TypeNews'):
        if obj.image and hasattr(obj.image, 'url'):
            image_url = obj.image.url
            if image_url.startswith("/http:/"):
                image_url = image_url.replace("/http:/", "http://")
            return image_url
        else:
            return None

    def update(self, instance, validated_data):
        try:
            with transaction.atomic():
                template = validated_data.pop('template', None)
                if template:
                    validated_data['template'] = template
                    type_news = super(TypeNewsDefaultSerializer, self).update(instance, validated_data)
                else:
                    instance.code = validated_data.get('code')
                    instance.description = validated_data.get('description')
                    instance.image = validated_data.get('image')
                    instance.info = validated_data.get('info')
                    instance.is_changing_of_the_guard = validated_data.get('is_changing_of_the_guard')
                    instance.is_active = validated_data.get('is_active')
                    instance.save(
                        update_fields=['code', 'description', 'image', 'info', 'is_changing_of_the_guard', 'is_active']
                    )
                    type_news = instance
        except ValueError as e:
            raise serializers.ValidationError(detail={"error": e})
        return type_news

    class Meta:
        model = TypeNews
        fields = serializers.ALL_FIELDS


class TypeNewsSimpleSerializer(DynamicFieldsMixin, serializers.ModelSerializer):
    image_display = serializers.SerializerMethodField(read_only=True)

    def get_image_display(self, obj: 'TypeNews'):
        # request = self.context.get('request')
        if obj.image and hasattr(obj.image, 'url'):
            image_url = obj.image.url
            return str(image_url)[1:] if str(image_url).startswith("/") else image_url
        else:
            return None

    class Meta:
        model = TypeNews
        exclude = ('info', 'template',)