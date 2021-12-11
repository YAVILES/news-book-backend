from django.shortcuts import render

# Create your views here.
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets, status
from rest_framework.filters import SearchFilter
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet

from .models import Client, Domain
from .serializers import ClientSerializer, DomainSerializer


class ClientViewSet(ModelViewSet):
    serializer_class = ClientSerializer
    queryset = Client.objects.all()
    filter_backends = [DjangoFilterBackend, SearchFilter]
    search_fields = ['name', 'domain_url']
    permission_classes = (AllowAny,)

    def create(self, request, *args, **kwargs):
        #self.perform_create(serializer)
        data = request.data
        tenant = Client(
            schema_name=data['schema_name'],
            name=data['name'],
            paid_until=data['paid_until'],
            on_trial=False
        )
        tenant.save()
        domain = Domain()
        domain.domain = data['domain']
        domain.tenant = tenant
        domain.is_primary = True
        domain.save()
        # headers = self.get_success_headers(serializer.data)
        return Response(ClientSerializer(tenant).data, status=status.HTTP_201_CREATED)

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


class DomainViewSet(ModelViewSet):
    serializer_class = DomainSerializer
    queryset = Domain.objects.all()
    filter_backends = [DjangoFilterBackend, SearchFilter]
    search_fields = ['domain']
    permission_classes = (AllowAny,)

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