# coding=utf-8
from django_restql.mixins import DynamicFieldsMixin
from rest_framework import serializers

from apps.core.models import TypeNews


class TypeNewsDefaultSerializer(DynamicFieldsMixin, serializers.ModelSerializer):
    info = serializers.CharField(required=False)
    template = serializers.JSONField(required=False, default=list)

    image_display = serializers.SerializerMethodField(read_only=True)

    def get_image_display(self, obj: 'TypeNews'):
        request = self.context.get('request')
        if obj.image and hasattr(obj.image, 'url'):
            image_url = obj.image.url
            return request.build_absolute_uri(image_url)
        else:
            return None

    def update(self, instance, validated_data):
        try:
            with transaction.atomic():
                template = validated_data.get('template', None)
                if template is None:
                    validated_data.pop('template')
                type_news = super(TypeNewsDefaultSerializer, self).update(instance, validated_data)
        except ValueError as e:
            raise serializers.ValidationError(detail={"error": e})
        return type_news

    class Meta:
        model = TypeNews
        fields = serializers.ALL_FIELDS

