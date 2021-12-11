from django_restql.mixins import DynamicFieldsMixin
from rest_framework import serializers

from apps.core.serializers import TypeNewsDefaultSerializer
from apps.main.models import TypePerson, Person, Vehicle, Material, News, Schedule, Location, Point


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
    owner_full_name = serializers.CharField(help_text="Nombre y apellido del propietario", read_only=True)

    class Meta:
        model = Vehicle
        fields = serializers.ALL_FIELDS


class MaterialDefaultSerializer(DynamicFieldsMixin, serializers.ModelSerializer):
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
    location = LocationDefaultSerializer(read_only=True)

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
