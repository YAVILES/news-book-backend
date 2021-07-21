# coding=utf-8
from django_restql.mixins import DynamicFieldsMixin
from rest_framework import serializers

from core.models import TypePerson, Person, ClassificationNews, TypeNews, Vehicle, Material, News


class TypePersonDefaultSerializer(DynamicFieldsMixin, serializers.ModelSerializer):
    class Meta:
        model = TypePerson
        fields = serializers.ALL_FIELDS


class PersonDefaultSerializer(DynamicFieldsMixin, serializers.ModelSerializer):
    type_person = TypePersonDefaultSerializer(read_only=True)

    class Meta:
        model = Person
        fields = serializers.ALL_FIELDS


class ClassificationNewsDefaultSerializer(DynamicFieldsMixin, serializers.ModelSerializer):
    class Meta:
        model = ClassificationNews
        fields = serializers.ALL_FIELDS


class TypeNewsDefaultSerializer(DynamicFieldsMixin, serializers.ModelSerializer):
    class Meta:
        model = TypeNews
        fields = serializers.ALL_FIELDS


class VehicleDefaultSerializer(DynamicFieldsMixin, serializers.ModelSerializer):
    class Meta:
        model = Vehicle
        fields = serializers.ALL_FIELDS


class MaterialDefaultSerializer(DynamicFieldsMixin, serializers.ModelSerializer):
    class Meta:
        model = Material
        fields = serializers.ALL_FIELDS


class NewsDefaultSerializer(DynamicFieldsMixin, serializers.ModelSerializer):
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
    employee = serializers.CharField(help_text="Ficha del trabajador que generó la novedad")

    class Meta:
        model = News
        fields = serializers.ALL_FIELDS
