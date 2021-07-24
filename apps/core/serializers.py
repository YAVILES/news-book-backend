# coding=utf-8
from django_restql.mixins import DynamicFieldsMixin
from rest_framework import serializers

from apps.core.models import TypeNews


class TypeNewsDefaultSerializer(DynamicFieldsMixin, serializers.ModelSerializer):
    info = serializers.JSONField(required=False, default=dict)
    image = serializers.SerializerMethodField(read_only=True)

    def get_image(self, obj: 'Category'):
        request = self.context.get('request')
        if obj.image and hasattr(obj.image, 'url'):
            image_url = obj.image.url
            print(image_url)
            return request.build_absolute_uri(image_url)
        else:
            return None

    class Meta:
        model = TypeNews
        fields = serializers.ALL_FIELDS

