from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from rest_framework.decorators import action

from .models import Client, Domain
from .serializers import ClientSerializer, DomainSerializer
from django.db import connections
from django_tenants.utils import get_tenant_database_alias
from apps.customers.models import Client
from apps.main.models import TypePerson
from rest_framework import status, mixins

class ClientViewSet(ModelViewSet):
    serializer_class = ClientSerializer
    queryset = Client.objects.all()
    filter_backends = [DjangoFilterBackend, SearchFilter]
    search_fields = ['name', 'email']
    permission_classes = (AllowAny,)
    authentication_classes = []

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def paginate_queryset(self, queryset):
        """
        Return a single page of results, or `None` if pagination is disabled.
        """
        not_paginator = self.request.query_params.get('not_paginator', None)
        if self.paginator is None or not_paginator:
            return None
        return self.paginator.paginate_queryset(queryset, self.request, view=self)

    @action(methods=['POST'], detail=False)
    def duplicate_type_persons(self, request):
        from django.db import connections
        from django_tenants.utils import get_tenant_database_alias
        from apps.customers.models import Client
        from apps.main.models import TypePerson

        # Cambiar al esquema `public`
        public_schema_name = "public"
        connection = connections[get_tenant_database_alias()]
        public_client = Client.objects.get(schema_name=public_schema_name)
        connection.set_tenant(public_client)

        # Obtener todos los tipos de personas del esquema `public`
        public_type_persons = TypePerson.objects.all()

        # Recorrer todos los clientes
        for client in Client.objects.all():
            # Cambiar al esquema del cliente
            connection.set_tenant(client)

            # Copiar los tipos de personas al esquema del cliente
            for type_person in public_type_persons:
                # Verificar si el tipo de persona ya existe en el esquema del cliente
                if not TypePerson.objects.filter(description=type_person.description).exists():
                    # Crear una copia del tipo de persona en el esquema del cliente
                    TypePerson.objects.create(
                        description=type_person.description,
                        priority=type_person.priority,
                        is_active=type_person.is_active,
                        is_institution=type_person.is_institution,
                        requires_company_data=type_person.requires_company_data,
                        requires_guide_number=type_person.requires_guide_number,
                    )

            print(f"Tipos de personas copiados al esquema del cliente: {client.schema_name}")

        # Volver al esquema `public` al finalizar
        connection.set_tenant(public_client)

        return Response({}, status=status.HTTP_200_OK)

class DomainViewSet(ModelViewSet):
    serializer_class = DomainSerializer
    queryset = Domain.objects.all()
    filter_backends = [DjangoFilterBackend, SearchFilter]
    search_fields = ['domain']
    permission_classes = (AllowAny,)
    authentication_classes = []

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def paginate_queryset(self, queryset):
        """
        Return a single page of results, or `None` if pagination is disabled.
        """
        not_paginator = self.request.query_params.get('not_paginator', None)
        if self.paginator is None or not_paginator:
            return None
        return self.paginator.paginate_queryset(queryset, self.request, view=self)