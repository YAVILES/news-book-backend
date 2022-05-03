from django.db import transaction
from django_restql.mixins import DynamicFieldsMixin
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from apps.core.serializers import TypeNewsDefaultSerializer
from apps.main.models import TypePerson, Person, Vehicle, Material, News, Schedule, Location, Point, EquipmentTools, \
    get_auto_code_material
from apps.setting.tasks import generate_notification_async


class TypePersonDefaultSerializer(DynamicFieldsMixin, serializers.ModelSerializer):
    class Meta:
        model = TypePerson
        fields = serializers.ALL_FIELDS


class PersonDefaultSerializer(DynamicFieldsMixin, serializers.ModelSerializer):
    type_person_display = TypePersonDefaultSerializer(read_only=True, source="type_person")
    type_person = serializers.PrimaryKeyRelatedField(
        queryset=TypePerson.objects.all(),
        required=True,
        help_text="Id del tipo de persona"
    )

    class Meta:
        model = Person
        fields = serializers.ALL_FIELDS


class VehicleDefaultSerializer(DynamicFieldsMixin, serializers.ModelSerializer):
    owner_full_name = serializers.CharField(help_text="Nombre y apellido del propietario")

    class Meta:
        model = Vehicle
        fields = serializers.ALL_FIELDS


class MaterialDefaultSerializer(DynamicFieldsMixin, serializers.ModelSerializer):
    code = serializers.CharField(required=False, allow_null=True)
    serial = serializers.CharField(required=False, allow_null=True)

    def create(self, validated_data):
        try:
            with transaction.atomic():
                code = validated_data.get('code', None)
                serial = validated_data.get('serial', None)
                if code is None or serial is None:
                    auto_code = get_auto_code_material()
                    if code is None:
                        validated_data['code'] = auto_code
                    if serial is None:
                        validated_data['serial'] = auto_code

                material = super(MaterialDefaultSerializer, self).create(validated_data)
                return material
        except ValidationError as error:
            raise serializers.ValidationError(detail={"error": error.detail})

    class Meta:
        model = Material
        fields = serializers.ALL_FIELDS


class LocationDefaultSerializer(DynamicFieldsMixin, serializers.ModelSerializer):
    class Meta:
        model = Location
        fields = serializers.ALL_FIELDS


class NewsDefaultSerializer(DynamicFieldsMixin, serializers.ModelSerializer):
    created_by = serializers.HiddenField(
        default=serializers.CurrentUserDefault())
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
    location_display = LocationDefaultSerializer(read_only=True)

    def create(self, validated_data):
        try:
            with transaction.atomic():
                info = validated_data.get('info')
                for key in list(info.keys()):
                    obj = info[key]
                    if 'materials' in obj:
                        if 'value' in obj['materials']:
                            for material in obj['materials']['value']:
                                equipment_tool, created = EquipmentTools.objects.update_or_create(
                                    serial=material['serial'],
                                    defaults={
                                        'description': material['description'],
                                        'mark': material['mark'],
                                        'model': material['model'],
                                        'color': material['color'],
                                        'year': material['year'],
                                        'license_plate': material['license_plate'],
                                    },
                                )

                new = super(NewsDefaultSerializer, self).create(validated_data)
                generate_notification_async.delay(new.id)
                return new
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
