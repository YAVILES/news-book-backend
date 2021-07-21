from django.contrib.auth.models import Group, User
from import_export.resources import ModelResource


class UserResource(ModelResource):
    class Meta:
        model = User
        exclude = ('id', 'created', 'updated',)
        export_order = ('id', 'email', 'name')


class RoleResource(ModelResource):
    class Meta:
        model = Group
        exclude = ('id', 'created', 'updated',)