from django import forms
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import UserChangeForm, AuthenticationForm
from django.contrib.auth.models import Group
from django.utils.translation import ugettext_lazy as _
from django_tenants.admin import TenantAdminMixin
from import_export.resources import ModelResource
from import_export.admin import ImportExportModelAdmin

from apps.security.models import User


class UserResource(ModelResource):
    class Meta:
        model = User
        exclude = ('id', 'created', 'updated',)
        export_order = ('id', 'email', 'name')


class RoleResource(ModelResource):
    class Meta:
        model = Group
        exclude = ('id', 'created', 'updated',)


class CustomUserChangeForm(UserChangeForm):
    class Meta(UserChangeForm.Meta):
        model = User


class UserResourceAdmin(ImportExportModelAdmin):
    resource_class = UserResource


class CustomUserAdmin(UserAdmin, ImportExportModelAdmin, TenantAdminMixin):
    form = CustomUserChangeForm
    list_display = ['code', 'email', 'name', 'last_name', 'is_staff', 'is_superuser', 'is_active']
    list_filter = ['code', 'email', 'is_active', 'is_staff', 'is_superuser']
    filter_horizontal = ['groups']
    fieldsets = (
        (None, {'fields': ('code', 'email', 'password',)}),
        (_('Personal info'), {'fields': ('name', 'last_name')}),
        (_('Permissions'), {
            'fields': ('is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        (_('Important dates'), {'fields': ('last_login',)}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2'),
        }),
    )
    search_fields = ('email',)
    ordering = ('email',)


admin.site.register(User, CustomUserAdmin)


class MyLoginForm(AuthenticationForm):
    """Extend login form"""
    email = forms.CharField(
        label=_("email"),
        max_length=30,
        widget=forms.TextInput(attrs={
            'title': 'Correo',
            'id': 'id_email',
            'name': 'email'
        })
    )
    password = forms.CharField(
        label=_("password"),
        widget=forms.PasswordInput(attrs={
            'title': 'Cotraseña',
            'id': 'id_password',
            'name': 'password'
        })
    )
