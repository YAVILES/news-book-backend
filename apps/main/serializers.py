from django.conf import settings
from django.db import transaction
from django_restql.mixins import DynamicFieldsMixin
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from apps.core.serializers import TypeNewsDefaultSerializer
from apps.customers.serializers import ClientSimpleSerializer
from apps.main.models import TypePerson, Person, Vehicle, Material, News, Schedule, Location, Point, EquipmentTools, \
    get_auto_code_material, get_auto_code_person
from apps.security.models import User
from apps.setting.models import Notification
from apps.setting.tasks import generate_notification_async, send_email


class TypePersonDefaultSerializer(DynamicFieldsMixin, serializers.ModelSerializer):
    class Meta:
        model = TypePerson
        fields = serializers.ALL_FIELDS


class PersonDefaultSerializer(DynamicFieldsMixin, serializers.ModelSerializer):
    code = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    type_person_display = TypePersonDefaultSerializer(read_only=True, source="type_person")
    type_person = serializers.PrimaryKeyRelatedField(
        queryset=TypePerson.objects.all(),
        required=True,
        help_text="Id del tipo de persona"
    )
    full_name = serializers.CharField(help_text="Nombre y apellido", read_only=True)

    def create(self, validated_data):
        try:
            with transaction.atomic():
                code = validated_data.get('code', None)
                if code is None or code == "":
                    auto_code = get_auto_code_person()
                    validated_data['code'] = auto_code

                person = super(PersonDefaultSerializer, self).create(validated_data)
                return person
        except ValidationError as error:
            raise serializers.ValidationError(detail={"error": error.detail})

    class Meta:
        model = Person
        fields = serializers.ALL_FIELDS


class VehicleDefaultSerializer(DynamicFieldsMixin, serializers.ModelSerializer):
    owner_full_name = serializers.CharField(help_text="Nombre y apellido del propietario")

    class Meta:
        model = Vehicle
        fields = serializers.ALL_FIELDS


class MaterialDefaultSerializer(DynamicFieldsMixin, serializers.ModelSerializer):
    code = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    serial = serializers.CharField(required=False, allow_null=True, allow_blank=True)

    def create(self, validated_data):
        try:
            with transaction.atomic():
                code = validated_data.get('code', None)
                serial = validated_data.get('serial', None)
                if code is None or code == "" or serial is None or serial == "":
                    auto_code = get_auto_code_material()
                    if code is None or code == "":
                        validated_data['code'] = auto_code
                    if serial is None or serial == "":
                        validated_data['serial'] = auto_code

                material = super(MaterialDefaultSerializer, self).create(validated_data)
                return material
        except ValidationError as error:
            raise serializers.ValidationError(detail={"error": error.detail})

    class Meta:
        model = Material
        fields = serializers.ALL_FIELDS


class MaterialScopeSerializer(DynamicFieldsMixin, serializers.ModelSerializer):
    code = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    name = serializers.SerializerMethodField(read_only=True)

    def get_name(self, material):
        return material.description

    class Meta:
        model = Material
        fields = ('code', 'name',)


class LocationDefaultSerializer(DynamicFieldsMixin, serializers.ModelSerializer):
    class Meta:
        model = Location
        fields = serializers.ALL_FIELDS


class NewsDefaultSerializer(DynamicFieldsMixin, serializers.ModelSerializer):
    created_by = serializers.HiddenField(default=serializers.CurrentUserDefault())
    materials = serializers.PrimaryKeyRelatedField(
        queryset=Material.objects.all(),
        many=True,
        required=False,
        help_text="Materiales de la novedad"
    )
    people = serializers.PrimaryKeyRelatedField(
        queryset=Person.objects.all(),
        many=True,
        required=False,
        help_text="Personas de la novedad"
    )
    vehicles = serializers.PrimaryKeyRelatedField(
        queryset=Vehicle.objects.all(),
        many=True,
        required=False,
        help_text="Vehiculos de la novedad"
    )
    employee = serializers.CharField(
        help_text="Ficha del trabajador que generó la novedad")
    template = serializers.JSONField(required=False, default=list)
    info = serializers.JSONField(required=False, default=dict)
    type_news_display = TypeNewsDefaultSerializer(read_only=True, source="type_news", exclude=('image_display',))
    location = serializers.PrimaryKeyRelatedField(
        queryset=Location.objects.all(),
        required=False,
        write_only=True,
        help_text="Libro donde se genera la novedad"
    )
    location_display = LocationDefaultSerializer(read_only=True, source="location")
    client_display = serializers.SerializerMethodField(read_only=True)
    link = serializers.SerializerMethodField(read_only=True)

    def get_link(self, obj):
        request = self.context.get('request')
        return settings.HOST_LINKS + "/#/viewlink/" + str(obj.id) + "/" + request.tenant.schema_name

    def get_client_display(self, obj):
        request = self.context.get('request')
        return ClientSimpleSerializer(request.tenant).data

    def create(self, validated_data):
        request = self.context.get('request')
        try:
            with transaction.atomic():
                info = validated_data.get('info', {})

                for key, obj in info.items():
                    try:
                        # Solo procesar si es un diccionario y tiene 'materials'
                        if isinstance(obj, dict) and 'materials' in obj:
                            materials_value = obj['materials']
                            # Verificar si materials_value es un diccionario con 'value'
                            if isinstance(materials_value, dict) and 'value' in materials_value:
                                materials_list = materials_value['value']
                                if isinstance(materials_list, list):
                                    for material in materials_list:
                                        if isinstance(material, dict):
                                            equipment_tool, created = EquipmentTools.objects.update_or_create(
                                                serial=material.get('serial', ''),
                                                defaults={
                                                    'description': material.get('description', ''),
                                                    'mark': material.get('mark', ''),
                                                    'model': material.get('model', ''),
                                                    'color': material.get('color', ''),
                                                    'year': material.get('year', ''),
                                                    'license_plate': material.get('license_plate', ''),
                                                },
                                            )
                    except (TypeError, AttributeError) as e:
                        print(f"Error procesando material en clave {key}: {str(e)}")
                        continue

                instance = super(NewsDefaultSerializer, self).create(validated_data)

                # Envió de notificaciones
                try:
                    notifications = Notification.objects.filter(
                        type_news_id=instance.type_news_id
                    )
                    for notif in notifications:
                        groups = notif.groups.all().values_list('id', flat=True)
                        emails = [
                            str(email)
                            for email in User.objects.filter(
                                groups__id__in=groups, is_active=True, email__isnull=False
                            ).values_list('email', flat=True).distinct()
                        ]

                        if instance.location:
                            send_email.delay(
                                instance.type_news.description,
                                notif.description + " " + instance.location.name +
                                " \n Para acceder usa el siguiente link " + settings.HOST_LINKS +
                                "/#/viewlink/" + str(instance.id) + "/" + request.tenant.schema_name,
                                emails
                            )
                        else:
                            send_email.delay(
                                instance.type_news.description,
                                notif.description +
                                "\n Para acceder usa el siguiente link " + settings.HOST_LINKS +
                                "/#/viewlink/" + str(instance.id) + "/" + request.tenant.schema_name,
                                emails
                            )
                except Exception as e:
                    print(e.__str__())
                    pass
                return instance
            return None
        except ValidationError as error:
            raise serializers.ValidationError(detail={"error": error.detail})

    class Meta:
        model = News
        fields = serializers.ALL_FIELDS


class ScheduleDefaultSerializer(DynamicFieldsMixin, serializers.ModelSerializer):
    start_time = serializers.TimeField(format="%H:%M")
    final_hour = serializers.TimeField(format="%H:%M")

    class Meta:
        model = Schedule
        fields = serializers.ALL_FIELDS


class PointDefaultSerializer(DynamicFieldsMixin, serializers.ModelSerializer):
    class Meta:
        model = Point
        fields = serializers.ALL_FIELDS


class EquipmentToolsDefaultSerializer(DynamicFieldsMixin, serializers.ModelSerializer):
    class Meta:
        model = EquipmentTools
        fields = serializers.ALL_FIELDS
