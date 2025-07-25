from cryptography.fernet import Fernet
from django.contrib.auth import password_validation
from django.contrib.auth.models import Permission, Group
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db import transaction
from django_restql.mixins import DynamicFieldsMixin
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.utils.translation import ugettext_lazy as _

from apps.main.models import Location
from apps.main.serializers import LocationDefaultSerializer
from apps.security.models import User


class ChangeSecurityCodeSerializer(serializers.ModelSerializer):
    code = serializers.CharField(required=True)
    password = serializers.CharField(required=True)

    class Meta:
        model = User
        fields = ('code', 'password',)


class UserCreateSerializer(serializers.ModelSerializer):
    groups = serializers.PrimaryKeyRelatedField(
        queryset=Group.objects.all(), many=True, required=False, write_only=True
    )
    security_user = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), required=False, write_only=True, allow_null=True
    )
    code = serializers.CharField(max_length=255, required=False)
    password = serializers.CharField(max_length=255, write_only=True, required=False)
    ficha = serializers.CharField(max_length=20, required=False, default=None, allow_null=True)
    is_superuser = serializers.BooleanField(required=False, read_only=True)
    is_staff = serializers.BooleanField(required=True)
    email = serializers.EmailField()
    info = serializers.JSONField(default=dict)
    locations = serializers.PrimaryKeyRelatedField(
        queryset=Location.objects.all(), required=False, write_only=True, many=True
    )

    def validate(self, attrs):
        password = attrs.get('password')
        if password:
            try:
                password_validation.validate_password(password)
            except ValidationError as error:
                raise serializers.ValidationError(
                    detail={"error": error.messages})
        return attrs

    def create(self, validated_data):
        request = self.context.get('request')
        password = validated_data.pop('password')
        email = validated_data.get('email')
        code = validated_data.get('code')
        books = validated_data.get('locations', None)
        if books:
            validated_data['locations'] = books
        validated_data['email'] = str(email).lower()

        schema_name = request.headers.get('X-Dts-Schema', 'public')
        validated_data['code'] = str(code).lower() + "@" + schema_name
        validated_data['schema_name'] = schema_name
        try:
            with transaction.atomic():
                user = super(UserCreateSerializer, self).create(validated_data)
                if password:
                    user.set_password(password)
                    user.save(update_fields=['password'])
        except ValidationError as error:
            raise serializers.ValidationError(detail={"error": error.messages})
        return validated_data

    def update(self, instance, validated_data):
        try:
            with transaction.atomic():
                password = validated_data.pop('password', None)
                user = super(UserCreateSerializer, self).update(instance, validated_data)
                if password:
                    user.set_password(password)
                    user.save(update_fields=['password'])
        except ValueError as e:
            raise serializers.ValidationError(detail={"error": e})
        return user

    class Meta:
        model = User
        fields = ('id', 'code', 'email', 'password', 'name', 'last_name', 'full_name', 'address', 'phone',
                  'is_superuser', 'is_staff', 'groups', 'info', 'is_active', 'security_user', 'ficha', 'is_oesvica',
                  'identification_number', 'locations', 'type_user',)


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    security_code = serializers.CharField()

    def validate(self, attrs):
        super().validate(attrs)
        refresh = self.get_token(self.user)
        key = Fernet.generate_key()
        f = Fernet(key)
        json_security = {
            "is_superuser": self.user.is_superuser,
            "is_oesvica": self.user.is_oesvica
        }
        security_data = f.encrypt(bytes(str(json_security), encoding='utf8'))

        from django.db import connection
        tenant = connection.tenant

        return {
            'token': str(refresh.access_token),
            'refresh': str(refresh),
            'jwt_id': self.user.jwt_id,
            'info': None,
            'danger': None,
            'warn': [],
            'name': self.user.full_name,
            "is_superuser": self.user.is_superuser,
            "security_data": security_data,
            "id": self.user.id,
            "type_user": self.user.type_user,
            "locations": self.user.locations.all().values_list("id", flat=True),
            "facial_recognition": tenant.facial_recognition
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
    permissions = PermissionDefaultSerializer(
        many=True, read_only=True, required=False)
    name = serializers.CharField(max_length=255, required=False)

    class Meta:
        model = Group
        fields = serializers.ALL_FIELDS


class UserSecuritySerializer(DynamicFieldsMixin, serializers.ModelSerializer):

    class Meta:
        model = User
        fields = ('id', 'code', 'email', 'password', 'name', 'last_name', 'full_name', 'type_user',)


class UserSimpleSerializer(DynamicFieldsMixin, serializers.ModelSerializer):
    is_superuser = serializers.BooleanField(required=False, read_only=True)
    security_user = UserSecuritySerializer(read_only=True)
    locations = LocationDefaultSerializer(read_only=True, many=True)
    groups_display = RoleDefaultSerializer(read_only=True, many=True, source="groups")

    class Meta:
        model = User
        fields = ('id', 'code', 'email', 'name', 'last_name', 'full_name', 'address', 'phone', 'is_superuser',
                  'is_staff', 'groups', 'info', 'is_active', 'security_user', 'ficha', 'is_oesvica',
                  'identification_number', 'locations', 'type_user', 'groups_display',)


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
            raise serializers.ValidationError(
                detail={"error": _('email invalid')})

        user.set_password(password)
        user.save(update_fields=['password'])
        return {'password': '', 'email': email}

    class Meta:
        fields = ('email', 'password',)
