from django.contrib import admin
from django.contrib import admin
from import_export.resources import ModelResource
from django_tenants.admin import TenantAdminMixin

# Register your models here.
from apps.main.models import TypePerson, Material, Vehicle, Person, News, Schedule, Location


class PersonResource(ModelResource):
    class Meta:
        model = Person
        exclude = ('id', 'created', 'updated',)


class TypePersonResource(ModelResource):
    class Meta:
        model = TypePerson
        exclude = ('id', 'created', 'updated',)


class NewsResource(ModelResource):
    class Meta:
        model = News
        exclude = ('id', 'created', 'updated',)


class VehicleResource(ModelResource):
    class Meta:
        model = Vehicle
        exclude = ('id', 'created', 'updated',)


class MaterialResource(ModelResource):
    class Meta:
        model = Material
        exclude = ('id', 'created', 'updated',)


class ScheduleResource(ModelResource):
    class Meta:
        model = Schedule
        exclude = ('id', 'created', 'updated',)


class LocationResource(ModelResource):
    class Meta:
        model = Location
        exclude = ('id', 'created', 'updated',)


@admin.register(TypePerson)
class TypePersonAdmin(TenantAdminMixin, admin.ModelAdmin):
    list_display = ('description', 'priority', 'is_active')


@admin.register(Person)
class PersonAdmin(TenantAdminMixin, admin.ModelAdmin):
    list_display = ('code', 'name', 'last_name', 'doc_ident')


@admin.register(Vehicle)
class VehicleAdmin(TenantAdminMixin, admin.ModelAdmin):
    list_display = ('license_plate',)


@admin.register(Material)
class MaterialAdmin(TenantAdminMixin, admin.ModelAdmin):
    list_display = ('code', 'serial', 'description',)


@admin.register(News)
class NewsAdmin(TenantAdminMixin, admin.ModelAdmin):
    list_display = ('message',)

@admin.register(Location)
class Locationdmin(TenantAdminMixin, admin.ModelAdmin):
    list_display = ('code', 'name',)