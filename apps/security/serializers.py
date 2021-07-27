# coding=utf-8
from django.contrib.auth import password_validation
from django.contrib.auth.models import Permission, Group
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django_restql.mixins import DynamicFieldsMixin
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.utils.translation import ugettext_lazy as _

from apps.security.models import User


class ChangeSecurityCodeSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(required=True)
    password = serializers.CharField(required=True)
    
    def validate(self, attrs):
        super().validate(attrs)
        try:
            user = User.objects.get(email=attrs.get('email'))
        except:
            raise serializers.ValidationError(detail={"email": _('email invalid')})

        return attrs

    class Meta:
        model = User
        fields = ('email',)


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    security_code = serializers.CharField()

    def validate(self, attrs):
        super().validate(attrs)
        refresh = self.get_token(self.user)
        return {
            'token': str(refresh.access_token),
            'refresh': str(refresh),
            'jwt_id': self.user.jwt_id,
            'info': None,
            'danger': None,
            'warn': [],
            'name': self.user.full_name,
            "is_superuser": self.user.is_superuser,
        }


class ContendTypeDefaultSerializer(DynamicFieldsMixin, serializers.ModelSerializer):
    class Meta:
        model = ContentType
        fields = serializers.ALL_FIELDS


class PermissionDefaultSerializer(DynamicFieldsMixin, serializers.ModelSerializer):
    name = serializers.CharField(max_length=255, required=True)
    codename = serializers.CharField(read_only=True, required=False)
    content_type = ContendTypeDefaultSerializer(read_only=True, required=False)

    class Meta:
        model = Permission
        fields = serializers.ALL_FIELDS


class RoleDefaultSerializer(DynamicFieldsMixin, serializers.ModelSerializer):
    class Meta:
        model = Group
        fields = serializers.ALL_FIELDS


class RoleFullSerializer(DynamicFieldsMixin, serializers.ModelSerializer):
    permissions = PermissionDefaultSerializer(many=True, read_only=True, required=False)
    name = serializers.CharField(max_length=255, required=False)

    class Meta:
        model = Group
        fields = serializers.ALL_FIELDS


class UserSimpleSerializer(DynamicFieldsMixin, serializers.ModelSerializer):
    is_superuser = serializers.BooleanField(required=False, read_only=True)

    class Meta:
        model = User
        fields = serializers.ALL_FIELDS


class ChangePasswordSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    password = serializers.CharField(max_length=255, required=True)

    def update(self, instance, validated_data):
        pass

    def create(self, validated_data):
        email = validated_data.get('email')
        password = validated_data.get('password')
        try:
            password_validation.validate_password(password)
        except ValidationError as error:
            raise serializers.ValidationError(detail={"error": error.messages})
        try:
            user = User.objects.get(email=email)
        except Exception as e:
            raise serializers.ValidationError(detail={"error": _('email invalid')})

        user.set_password(password)
        user.save(update_fields=['password'])
        return {'password': '', 'email': email}

    class Meta:
        fields = ('email', 'password',)

