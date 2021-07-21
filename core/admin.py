from django.contrib import admin
from django_tenants.admin import TenantAdminMixin
from import_export.resources import ModelResource

from core.models import Person, TypePerson, ClassificationNews, TypeNews, Vehicle, Material, News


@admin.register(TypePerson)
class TypePersonAdmin(TenantAdminMixin, admin.ModelAdmin):
    list_display = ('description', 'priority', 'status')


class TypePersonResource(ModelResource):
    class Meta:
        model = TypePerson
        exclude = ('id', 'created', 'updated',)


@admin.register(Person)
class PersonAdmin(TenantAdminMixin, admin.ModelAdmin):
    list_display = ('code', 'name', 'last_name', 'doc_ident')


class PersonResource(ModelResource):
    class Meta:
        model = Person
        exclude = ('id', 'created', 'updated',)


@admin.register(ClassificationNews)
class ClassificationNewsAdmin(TenantAdminMixin, admin.ModelAdmin):
    list_display = ('description',)


class ClassificationNewsResource(ModelResource):
    class Meta:
        model = ClassificationNews
        exclude = ('id', 'created', 'updated',)


@admin.register(TypeNews)
class TypeNewsAdmin(TenantAdminMixin, admin.ModelAdmin):
    list_display = ('description',)


class TypeNewsResource(ModelResource):
    class Meta:
        model = TypeNews
        exclude = ('id', 'created', 'updated',)


@admin.register(Vehicle)
class VehicleAdmin(TenantAdminMixin, admin.ModelAdmin):
    list_display = ('license_plate',)


class VehicleResource(ModelResource):
    class Meta:
        model = Vehicle
        exclude = ('id', 'created', 'updated',)


@admin.register(Material)
class MaterialAdmin(TenantAdminMixin, admin.ModelAdmin):
    list_display = ('code', 'serial', 'description',)


class MaterialResource(ModelResource):
    class Meta:
        model = Material
        exclude = ('id', 'created', 'updated',)


@admin.register(News)
class NewsAdmin(TenantAdminMixin, admin.ModelAdmin):
    list_display = ('message', 'created_by',)


class NewsResource(ModelResource):
    class Meta:
        model = News
        exclude = ('id', 'created', 'updated',)
