from django.contrib import admin
from django.contrib import admin
from import_export.resources import ModelResource
from django_tenants.admin import TenantAdminMixin

# Register your models here.
from apps.main.models import TypePerson, Material, Vehicle, Person, News
from apps.setting.models import Notification, GroupNotification


@admin.register(Notification)
class NotificationAdmin(TenantAdminMixin, admin.ModelAdmin):
    list_display = ('description',)


class NotificationResource(ModelResource):
    class Meta:
        model = Notification
        exclude = ('id', 'created', 'updated',)


@admin.register(GroupNotification)
class GroupNotificationAdmin(TenantAdminMixin, admin.ModelAdmin):
    list_display = ('id', 'group', 'notification',)
