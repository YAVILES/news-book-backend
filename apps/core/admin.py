from django.contrib import admin
from import_export.resources import ModelResource
from django_tenants.admin import TenantAdminMixin

from apps.core.models import TypeNews


class TypeNewsResource(ModelResource):
    class Meta:
        model = TypeNews
        exclude = ('id', 'created', 'updated',)


@admin.register(TypeNews)
class TypeNewsAdmin(TenantAdminMixin, admin.ModelAdmin):
    list_display = ('description',)
    exclude = ('info',)
