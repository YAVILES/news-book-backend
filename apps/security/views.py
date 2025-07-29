import requests
import tablib
import string
import random

from django.core.exceptions import ObjectDoesNotExist
from django.utils.translation import ugettext_lazy as _
from django.conf import settings

from django.contrib.auth.models import Group
from django.core.mail import EmailMultiAlternatives
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status, serializers
from rest_framework.decorators import action
from rest_framework.filters import SearchFilter
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet, GenericViewSet
from rest_framework_simplejwt.views import TokenObtainPairView
from tablib import Dataset
from django_filters import rest_framework as filters
from .admin import UserResource, RoleResource
from .models import User
from .serializers import UserSimpleSerializer, CustomTokenObtainPairSerializer, RoleDefaultSerializer, \
    ChangeSecurityCodeSerializer, ChangePasswordSerializer, UserCreateSerializer
from ..main.serializers import LocationDefaultSerializer


class ValidUser(GenericViewSet):
    permission_classes = (AllowAny,)
    authentication_classes = []

    def get_serializer_class(self):
        if self.action == 'request_security_code':
            return ChangeSecurityCodeSerializer
        if self.action == 'change_password':
            return ChangePasswordSerializer

    @action(methods=['POST', ], detail=False)
    def request_security_code(self, request):
        serializer = self.get_serializer(data=request.data, context=self.get_serializer_context())
        if serializer.is_valid():
            code_user = serializer.data["code"]
            password_user = serializer.data["password"]
            try:
                user: User = User.objects.get(code=code_user)
            except ObjectDoesNotExist:
                raise serializers.ValidationError(detail={"error": _('El usuario no se encuentra registrado')})

            if user.is_authenticated:
                serializers.ValidationError(detail={"error": "Este usuario ya tiene una session activa"})
            else:
                pass
            if not user.check_password(password_user):
                raise serializers.ValidationError(detail={"error": _('Contraseña inválida')})

            if not user.is_active:
                raise serializers.ValidationError(detail={"error": _('Usuario inactivo')})

            if (not user.is_superuser and user.type_user != User.ADMINISTRATOR) and not user.locations:
                raise serializers.ValidationError(detail={"error": _('Debes tener al menos un libro asignado')})

            chars = string.ascii_uppercase + string.digits
            code = ''.join(random.choice(chars) for _ in range(8))

            if (user.security_user and user.security_user.phone) or user.phone:
                try:
                    requests.post(
                        url=settings.API_WHATSAPP,
                        data={
                            "phoneNumber": user.security_user.phone
                            if user.security_user and user.security_user.phone else user.phone,
                            "message": f'Código de Seguridad: {code}'
                        }
                    )
                except Exception:
                    pass

            try:
                if user.security_user and user.security_user.email:
                    destine_email = user.security_user.email
                else:
                    destine_email = user.email

                if destine_email:
                    email = EmailMultiAlternatives(
                        'Código de Seguridad',
                        code,
                        settings.EMAIL_HOST_USER,
                        [destine_email]
                    )
                    #email.attach_alternative(content, 'text/html')
                    email.send()
            except Exception as e:
                serializers.ValidationError(detail={"error": "No fue posible enviar el código de seguridad", "msg": e})

            user.is_verified_security_code = False
            user.security_code = code
            user.save(update_fields=['security_code'])
            return Response({
                'security_code': code,
                'locations': LocationDefaultSerializer(user.locations.all(), many=True).data
            }, status=status.HTTP_200_OK)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(methods=['POST', ], detail=False)
    def change_password(self, request):
        """
            Cambia la contraseña del usuario
        """
        serializer = self.get_serializer(data=request.data, context=self.get_serializer_context())
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserFilter(filters.FilterSet):

    class Meta:
        model = User
        fields = ['name', 'last_name', 'email']


# Create your views here.


class UserViewSet(ModelViewSet):
    queryset = User.objects.all()
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_class = UserFilter
    serializer_class = UserSimpleSerializer
    search_fields = ['name', 'last_name', 'email', 'code']
    permission_classes = (AllowAny,)

    def paginate_queryset(self, queryset):
        """
        Return a single page of results, or `None` if pagination is disabled.
        """
        not_paginator = self.request.query_params.get('not_paginator', None)
        if self.paginator is None or not_paginator:
            return None
        return self.paginator.paginate_queryset(queryset, self.request, view=self)

    def get_queryset(self):
        queryset = self.queryset

        # Superuser can see everything
        if self.request.user.is_superuser:
            return queryset

        # Staff can see everything except superusers
        if self.request.user.is_staff:
            return queryset.filter(is_superuser=False)

        # Rest of users can see themselves
        # if self.action == 'retrieve':
        #    return queryset.filter(pk=self.request.user.pk)

        return queryset.filter(is_superuser=False)
        # Can't list users
        # return queryset.none()

    def get_serializer_class(self):
        if self.action in ['create', 'update']:
            return UserCreateSerializer
        else:
            return UserSimpleSerializer

    @action(methods=['GET', ], detail=False)
    def current(self, request):
        return Response(UserSimpleSerializer(request.user).data)

    @action(methods=['GET'], detail=False)
    def export(self, request):
        dataset = UserResource().export()
        return Response(dataset.csv, status=status.HTTP_200_OK)

    @action(methods=['POST'], detail=False)
    def _import(self, request):
        try:
            resource = UserResource()
            errors = []
            invalids = []
            if request.FILES:
                file = request.FILES['file']
                data_set = Dataset()
                data_set.load(file.read())
                result = resource.import_data(data_set, dry_run=True)  # Test the data import
            else:
                headers = request.data['headers']
                data_set = tablib.Dataset(headers=headers)
                for d in request.data['data']:
                    data_set.append(d)
                result = resource.import_data(data_set, dry_run=True)

            if result.has_errors() or len(result.invalid_rows) > 0:
                for row in result.invalid_rows:
                    invalids.append(
                        {
                            "row": row.number + 1,
                            "error": row.error,
                            "error_dict": row.error_dict,
                            "values": row.values
                        }
                    )

                for row in result.row_errors():
                    err = row[1]
                    errors.append(
                        {
                            "errors": [e.error.__str__() for e in err],
                            "values": err[0].row,
                            "row": row[0]
                        }
                    )

                return Response({
                    "rows_error": errors,
                    "invalid_rows": invalids,
                    "totals": result.totals,
                    "total_rows": result.total_rows,
                }, status=status.HTTP_400_BAD_REQUEST)
            else:
                result = resource.import_data(data_set, dry_run=False)  # Actually import now
                return Response({
                    "totals": result.totals,
                    "total_rows": result.total_rows,
                }, status=status.HTTP_200_OK)
        except ValueError as e:
            return Response(e, status=status.HTTP_400_BAD_REQUEST)

    @action(methods=['GET'], detail=False)
    def field_options(self, request):
        field = self.request.query_params.get('field', None)
        fields = self.request.query_params.getlist('fields', None)
        if fields:
            try:
                data = {}
                for field in fields:
                    data[field] = []
                    for c in User._meta.get_field(field).choices:
                        data[field].append({
                            "value": c[0],
                            "description": c[1]
                        })
                return Response(data, status=status.HTTP_200_OK)
            except ValueError as e:
                return Response(e, status=status.HTTP_400_BAD_REQUEST)
        elif field:
            try:
                choices = []
                for c in User._meta.get_field(field).choices:
                    choices.append({
                        "value": c[0],
                        "description": c[1]
                    })
                return Response(choices, status=status.HTTP_200_OK)
            except ValueError as e:
                return Response(e, status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response({"error": "the field parameter is mandatory"}, status=status.HTTP_400_BAD_REQUEST)


class RoleViewSet(ModelViewSet):
    queryset = Group.objects.all()
    serializer_class = RoleDefaultSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter]
    search_fields = ['name']
    permission_classes = (AllowAny,)

    def paginate_queryset(self, queryset):
        """
        Return a single page of results, or `None` if pagination is disabled.
        """
        not_paginator = self.request.query_params.get('not_paginator', None)
        if self.paginator is None or not_paginator:
            return None
        return self.paginator.paginate_queryset(queryset, self.request, view=self)

    @action(methods=['GET'], detail=False)
    def export(self, request):
        dataset = RoleResource().export()
        return Response(dataset.csv, status=status.HTTP_200_OK)

    @action(methods=['POST'], detail=False)
    def _import(self, request):
        try:
            resource = RoleResource()
            errors = []
            invalids = []
            if request.FILES:
                file = request.FILES['file']
                data_set = Dataset()
                data_set.load(file.read())
                result = resource.import_data(data_set, dry_run=True)  # Test the data import
            else:
                headers = request.data['headers']
                data_set = tablib.Dataset(headers=headers)
                for d in request.data['data']:
                    data_set.append(d)
                result = resource.import_data(data_set, dry_run=True)

            if result.has_errors() or len(result.invalid_rows) > 0:
                for row in result.invalid_rows:
                    invalids.append(
                        {
                            "row": row.number + 1,
                            "error": row.error,
                            "error_dict": row.error_dict,
                            "values": row.values
                        }
                    )

                for row in result.row_errors():
                    err = row[1]
                    errors.append(
                        {
                            "errors": [e.error.__str__() for e in err],
                            "values": err[0].row,
                            "row": row[0]
                        }
                    )

                return Response({
                    "rows_error": errors,
                    "invalid_rows": invalids,
                    "totals": result.totals,
                    "total_rows": result.total_rows,
                }, status=status.HTTP_400_BAD_REQUEST)
            else:
                result = resource.import_data(data_set, dry_run=False)  # Actually import now
                return Response({
                    "totals": result.totals,
                    "total_rows": result.total_rows,
                }, status=status.HTTP_200_OK)
        except ValueError as e:
            return Response(e, status=status.HTTP_400_BAD_REQUEST)

    @action(methods=['GET'], detail=False)
    def field_options(self, request):
        field = self.request.query_params.get('field', None)
        fields = self.request.query_params.getlist('fields', None)
        if fields:
            try:
                data = {}
                for field in fields:
                    data[field] = []
                    for c in Group._meta.get_field(field).choices:
                        data[field].append({
                            "value": c[0],
                            "description": c[1]
                        })
                return Response(data, status=status.HTTP_200_OK)
            except ValueError as e:
                return Response(e, status=status.HTTP_400_BAD_REQUEST)
        elif field:
            try:
                choices = []
                for c in Group._meta.get_field(field).choices:
                    choices.append({
                        "value": c[0],
                        "description": c[1]
                    })
                return Response(choices, status=status.HTTP_200_OK)
            except ValueError as e:
                return Response(e, status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response({"error": "the field parameter is mandatory"}, status=status.HTTP_400_BAD_REQUEST)


class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer
