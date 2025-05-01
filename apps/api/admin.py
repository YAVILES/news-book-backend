from django.contrib import admin
from .models import APIConsumer, APIConsumerTenant

class APIConsumerTenantInline(admin.TabularInline):
    model = APIConsumerTenant
    extra = 1

@admin.register(APIConsumer)
class APIConsumerAdmin(admin.ModelAdmin):
    inlines = [APIConsumerTenantInline]
    list_display = ('name', 'is_active', 'has_full_access', 'created_at')
    list_editable = ('is_active', 'has_full_access')
    readonly_fields = ('token', 'last_used_at')
    search_fields = ('name', 'token')
    list_filter = ('is_active', 'has_full_access')