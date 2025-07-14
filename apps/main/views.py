import tablib
from django.db import connections
from django.db.models import CharField, Q, Func, Value, TextField
from django.db.models.functions import Cast
from django_filters.rest_framework import DjangoFilterBackend
from django_tenants.utils import get_tenant_database_alias
from rest_framework import status, mixins
from rest_framework.decorators import action
from rest_framework.filters import SearchFilter
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet, GenericViewSet
from tablib import Dataset
from django_filters import rest_framework as filters

from django.db.models.fields import BooleanField
from django.db.models.expressions import ExpressionWrapper
from datetime import datetime

# Create your views here.
from apps.customers.models import Client
from apps.main.admin import VehicleResource, NewsResource, MaterialResource, TypePersonResource, PersonResource, \
    ScheduleResource, LocationResource, PointResource
from apps.main.models import AccessEntry, Vehicle, TypePerson, Person, Material, News, Schedule, Location, Point, EquipmentTools, AccessGroup
from apps.main.serializers import AccessEntrySerializer, VehicleDefaultSerializer, TypePersonDefaultSerializer, PersonDefaultSerializer, \
    MaterialDefaultSerializer, NewsDefaultSerializer, ScheduleDefaultSerializer, LocationDefaultSerializer, \
    PointDefaultSerializer, EquipmentToolsDefaultSerializer, AccessGroupSerializer

class TypePersonFilter(filters.FilterSet):
    class Meta:
        model = TypePerson
        fields = ['priority', 'is_institution', 'requires_company_data', 'requires_guide_number', 'requires_access_verification']

class TypePersonViewSet(ModelViewSet):
    queryset = TypePerson.objects.all()
    serializer_class = TypePersonDefaultSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter]
    search_fields = ['description']
    permission_classes = (AllowAny,)
    filterset_class = TypePersonFilter 
    
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

    @action(methods=['GET'], detail=False)
    def export(self, request):
        dataset = TypePersonResource().export()
        return Response(dataset.csv, status=status.HTTP_200_OK)

    @action(methods=['POST'], detail=False)
    def _import(self, request):
        try:
            resource = TypePersonResource()
            errors = []
            invalids = []
            if request.FILES:
                file = request.FILES['file']
                data_set = Dataset()
                data_set.load(file.read())
                result = resource.import_data(
                    data_set, dry_run=True)  # Test the data import
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
                result = resource.import_data(
                    data_set, dry_run=False)  # Actually import now
                return Response({
                    "totals": result.totals,
                    "total_rows": result.total_rows,
                }, status=status.HTTP_200_OK)
        except ValueError as e:
            return Response(e, status=status.HTTP_400_BAD_REQUEST)


class PersonFilter(filters.FilterSet):
    requires_access_verification = filters.BooleanFilter(method='filter_requires_access_verification')

    class Meta:
        model = Person
        fields = ['code', 'doc_ident', 'blacklist', 'type_person_id', 'is_active', 'requires_access_verification']

    def filter_requires_access_verification(self, queryset, name, value):
        if value:
            return queryset.filter(type_person__requires_access_verification=True)
        return queryset

class PersonViewSet(ModelViewSet):
    queryset = Person.objects.all()
    serializer_class = PersonDefaultSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_class = PersonFilter
    search_fields = ['code', 'name', 'last_name', 'doc_ident', 'blacklist_reason']
    permission_classes = (AllowAny,)

    def paginate_queryset(self, queryset):
        """
        Return a single page of results, or `None` if pagination is disabled.
        """
        not_paginator = self.request.query_params.get('not_paginator', None)
        if self.paginator is None or not_paginator:
            return None
        return self.paginator.paginate_queryset(queryset, self.request, view=self)

    @action(methods=['GET'], detail=False, url_path='get-person')
    def get_person_by_identification(self, request):
        identification = request.query_params.get('identification', None)
        try:
            person = Person.objects.get(doc_ident=identification)
        except Person.DoesNotExist:
            return Response({
                "person": None,
                "blacklist": False,
                "has_access": False,
                "message": "La persona no existe"
            }, status=status.HTTP_200_OK)
        data = PersonDefaultSerializer(person).data
        # Verificar blacklist
        blacklist = person.blacklist
    
        if blacklist:
            return Response({
                "person": data,
                "blacklist": True,
                "has_access": False,
                "message": "Persona bloqueada"
            }, status=status.HTTP_200_OK)


        if person.type_person.requires_access_verification:
            # Buscar accesos registrados
            all_accesses = AccessEntry.objects.filter(Q(persons=person) | Q(group__persons=person))
            # Chequear si tiene acceso vigente
            now = datetime.now()
            has_access = False
            access_details = None
            for access in all_accesses:
                if access.access_type == AccessEntry.SINGLE:
                    if access.date_start and access.date_end:
                        if access.date_start <= now.date() <= access.date_end:
                            if access.start_time <= now.time() <= access.end_time:
                                has_access = True
                                access_details = AccessEntrySerializer(access).data
                                break
                elif access.access_type == AccessEntry.RECURRING:
                    if access.week_days and now.strftime('%A') in access.week_days:
                        if access.date_start <= now.date() <= access.date_end:
                            if access.start_time <= now.time() <= access.end_time:
                                has_access = True
                                access_details = AccessEntrySerializer(access).data
                                break
                    if access.specific_days and now.day in access.specific_days:
                        if access.date_start <= now.date() <= access.date_end:
                            if access.start_time <= now.time() <= access.end_time:
                                has_access = True
                                access_details = AccessEntrySerializer(access).data
                                break
            if has_access:
                return Response({
                    "person": data,
                    "blacklist": False,
                    "has_access": True,
                    "access_details": access_details,
                    "message": "Acceso permitido",
                    "access_list": []
                }, status=status.HTTP_200_OK)
            # Buscar el próximo acceso futuro (single o recurrente)
            future_accesses = []
            for access in all_accesses:
                if access.access_type == AccessEntry.SINGLE:
                    if access.date_start and access.date_end and access.date_end >= now.date():
                        if access.date_start >= now.date() or (access.date_start <= now.date() <= access.date_end):
                            future_accesses.append(access)
                elif access.access_type == AccessEntry.RECURRING:
                    if access.week_days or access.specific_days:
                        if access.date_start >= now.date() or (access.date_start <= now.date() <= access.date_end):
                            future_accesses.append(access)
                        
            future_accesses = sorted(future_accesses, key=lambda a: (
                a.date_start if a.access_type == AccessEntry.SINGLE else now.date(),
                a.start_time
            ))
            next_access = future_accesses[0] if future_accesses else None
            access_list = [AccessEntrySerializer(next_access).data] if next_access else []
            return Response({
                "person": data,
                "blacklist": False,
                "has_access": False,
                "message": "No tiene acceso permitido en este momento",
                "access_list": access_list
            }, status=status.HTTP_200_OK)
        else:
            return Response({
                "person": data,
                "blacklist": False,
                "has_access": True,
                "message": "",
                "access_list": []
            }, status=status.HTTP_200_OK)

    @action(methods=['GET'], detail=False)
    def export(self, request):
        dataset = PersonResource().export()
        return Response(dataset.csv, status=status.HTTP_200_OK)

    @action(methods=['POST'], detail=False)
    def _import(self, request):
        try:
            resource = PersonResource()
            errors = []
            invalids = []
            if request.FILES:
                file = request.FILES['file']
                data_set = Dataset()
                data_set.load(file.read())
                result = resource.import_data(
                    data_set, dry_run=True)  # Test the data import
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
                result = resource.import_data(
                    data_set, dry_run=False)  # Actually import now
                return Response({
                    "totals": result.totals,
                    "total_rows": result.total_rows,
                }, status=status.HTTP_200_OK)
        except ValueError as e:
            return Response(e, status=status.HTTP_400_BAD_REQUEST)


class VehicleViewSet(ModelViewSet):
    queryset = Vehicle.objects.all()
    serializer_class = VehicleDefaultSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter]
    search_fields = ['license_plate']
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
        dataset = VehicleResource().export()
        return Response(dataset.csv, status=status.HTTP_200_OK)

    @action(methods=['POST'], detail=False)
    def _import(self, request):
        try:
            resource = VehicleResource()
            errors = []
            invalids = []
            if request.FILES:
                file = request.FILES['file']
                data_set = Dataset()
                data_set.load(file.read())
                result = resource.import_data(
                    data_set, dry_run=True)  # Test the data import
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
                result = resource.import_data(
                    data_set, dry_run=False)  # Actually import now
                return Response({
                    "totals": result.totals,
                    "total_rows": result.total_rows,
                }, status=status.HTTP_200_OK)
        except ValueError as e:
            return Response(e, status=status.HTTP_400_BAD_REQUEST)


class MaterialViewSet(ModelViewSet):
    queryset = Material.objects.all()
    serializer_class = MaterialDefaultSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter]
    search_fields = ['description', 'code', 'serial']
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
        dataset = MaterialResource().export()
        return Response(dataset.csv, status=status.HTTP_200_OK)

    @action(methods=['POST'], detail=False)
    def _import(self, request):
        try:
            resource = MaterialResource()
            errors = []
            invalids = []
            if request.FILES:
                file = request.FILES['file']
                data_set = Dataset()
                data_set.load(file.read())
                result = resource.import_data(
                    data_set, dry_run=True)  # Test the data import
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
                result = resource.import_data(
                    data_set, dry_run=False)  # Actually import now
                return Response({
                    "totals": result.totals,
                    "total_rows": result.total_rows,
                }, status=status.HTTP_200_OK)
        except ValueError as e:
            return Response(e, status=status.HTTP_400_BAD_REQUEST)


class NewsFilter(filters.FilterSet):
    number = filters.NumberFilter(lookup_expr='icontains')
    employee = filters.CharFilter(lookup_expr='icontains')
    template = filters.CharFilter(lookup_expr='icontains')
    info = filters.CharFilter(lookup_expr='icontains')
    min_number = filters.NumberFilter(field_name="number", lookup_expr='gte')
    max_number = filters.NumberFilter(field_name="number", lookup_expr='lte')
    min_created = filters.DateFilter(field_name="created", lookup_expr='gte')
    max_created = filters.DateFilter(field_name="created", lookup_expr='lte')
    type_news = filters.NumberFilter(lookup_expr='icontains')
    contains_attached_files = filters.BooleanFilter(method='filter_contains_attached_files')
    person_type = filters.CharFilter(method='filter_by_person_type')

    class Meta:
        model = News
        fields = ['employee', 'number', 'template', 'info', 'location__code', 'location__name', 'min_number',
                  'max_number', 'min_created', 'max_created', 'type_news_id', 'contains_attached_files']

    def filter_contains_attached_files(self, queryset, name, value):
        """
        Filtro mejorado que verifica archivos adjuntos con contenido válido
        """
        # Convertimos el JSON a texto para buscar patrones
        queryset = queryset.annotate(
            info_text=Cast('info', TextField())
        )

        # Patrones para buscar
        if value:
            return queryset.filter(
                Q(info_text__contains='"ATTACHED_FILE_') &
                (
                    # Para array no vacío: "attachedFiles": [...elementos...]
                        Q(info_text__contains='"attachedFiles": [') &
                        ~Q(info_text__contains='"attachedFiles": []') |
                        # Para string no vacío: "attachedFiles": "valor"
                        Q(info_text__contains='"attachedFiles": "') &
                        ~Q(info_text__contains='"attachedFiles": ""')
                )
            )
        else:
            return queryset.exclude(
                Q(info_text__contains='"ATTACHED_FILE_') &
                Q(info_text__contains='"attachedFiles": [')
            )

    def filter_by_person_type(self, queryset, name, value):
        """
        Filtra novedades que contengan el tipo de persona especificado
        value: ID del tipo de persona a filtrar (como string)
        """
        if not value:
            return queryset

        # Convertimos el JSON a texto para buscar patrones
        queryset = queryset.annotate(
            info_text=Cast('info', TextField())
        )

        # Buscamos el patrón: "PERSON_" seguido de cualquier cosa y luego "type_person": "valor"
        return queryset.filter(
            Q(info_text__contains='"PERSON_') &
            Q(info_text__contains=f'"type_person": "{value}"')
        )

class NewsViewSet(ModelViewSet):
    queryset = News.objects.all().order_by('-number')
    serializer_class = NewsDefaultSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = NewsFilter

    permission_classes = (AllowAny,)

    def create(self, request, *args, **kwargs):
        data = request.data
        if 'location' in request.headers and request.headers['location']:
            data['location'] = request.headers['location']
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def get_queryset(self):
        queryset = super(NewsViewSet, self).get_queryset()
        search = self.request.query_params.get('search', None)
        if search is None:
            return queryset
        else:
            return queryset.annotate(
                info_format=Cast('info', output_field=CharField()),
                template_format=Cast('template', output_field=CharField())
            ).filter(
                Q(info_format__contains=search) |
                Q(number__icontains=search) |
                Q(template_format__icontains=search) |
                Q(employee__icontains=search) |
                Q(type_news__description__icontains=search) |
                Q(location__code__icontains=search) |
                Q(location__name__icontains=search)
            )

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())

        if 'location' in request.headers and request.headers['location'] and request.headers['location'] != '' and \
                request.headers['location'] is not None:
            queryset = queryset.filter(location_id=request.headers['location'])

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True, context=self.get_serializer_context())
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True, context=self.get_serializer_context())
        return Response(serializer.data)

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
        dataset = NewsResource().export()
        return Response(dataset.csv, status=status.HTTP_200_OK)

    @action(methods=['POST'], detail=False)
    def _import(self, request):
        try:
            resource = NewsResource()
            errors = []
            invalids = []
            if request.FILES:
                file = request.FILES['file']
                data_set = Dataset()
                data_set.load(file.read())
                result = resource.import_data(
                    data_set, dry_run=True)  # Test the data import
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
                result = resource.import_data(
                    data_set, dry_run=False)  # Actually import now
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
                    for c in News._meta.get_field(field).choices:
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
                for c in News._meta.get_field(field).choices:
                    choices.append({
                        "value": c[0],
                        "description": c[1]
                    })
                return Response(choices, status=status.HTTP_200_OK)
            except ValueError as e:
                return Response(e, status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response({"error": "the field parameter is mandatory"}, status=status.HTTP_400_BAD_REQUEST)


class NewsLinkViewSet(mixins.RetrieveModelMixin, GenericViewSet):
    queryset = News.objects.all()
    serializer_class = NewsDefaultSerializer
    authentication_classes = []
    permission_classes = (AllowAny,)

    def retrieve(self, request, *args, **kwargs):
        schema_name = self.request.query_params.get('schema_name', None)
        connection = connections[get_tenant_database_alias()]
        client = Client.objects.get(schema_name=schema_name)
        connection.set_tenant(client, True)
        new = self.get_object()
        location = ""
        try:
            if new.location:
                location = new.location.name
        except ValueError:
            pass
        serializer_data = self.get_serializer(new, context=self.get_serializer_context()).data
        data = {
            "new": serializer_data,
            "client": client.name,
            "location": location
        }
        return Response(data, status=status.HTTP_200_OK)


class ScheduleViewSet(ModelViewSet):
    queryset = Schedule.objects.all()
    serializer_class = ScheduleDefaultSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter]
    search_fields = ['description']
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

    @action(methods=['GET'], detail=False)
    def export(self, request):
        dataset = ScheduleResource().export()
        return Response(dataset.csv, status=status.HTTP_200_OK)

    @action(methods=['POST'], detail=False)
    def _import(self, request):
        try:
            resource = ScheduleResource()
            errors = []
            invalids = []
            if request.FILES:
                file = request.FILES['file']
                data_set = Dataset()
                data_set.load(file.read())
                result = resource.import_data(
                    data_set, dry_run=True)  # Test the data import
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
                result = resource.import_data(
                    data_set, dry_run=False)  # Actually import now
                return Response({
                    "totals": result.totals,
                    "total_rows": result.total_rows,
                }, status=status.HTTP_200_OK)
        except ValueError as e:
            return Response(e, status=status.HTTP_400_BAD_REQUEST)


class LocationViewSet(ModelViewSet):
    queryset = Location.objects.all()
    serializer_class = LocationDefaultSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter]
    search_fields = ['code', 'name']
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

    @action(methods=['GET'], detail=False)
    def export(self, request):
        dataset = LocationResource().export()
        return Response(dataset.csv, status=status.HTTP_200_OK)

    @action(methods=['POST'], detail=False)
    def _import(self, request):
        try:
            resource = LocationResource()
            errors = []
            invalids = []
            if request.FILES:
                file = request.FILES['file']
                data_set = Dataset()
                data_set.load(file.read())
                result = resource.import_data(
                    data_set, dry_run=True)  # Test the data import
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
                result = resource.import_data(
                    data_set, dry_run=False)  # Actually import now
                return Response({
                    "totals": result.totals,
                    "total_rows": result.total_rows,
                }, status=status.HTTP_200_OK)
        except ValueError as e:
            return Response(e, status=status.HTTP_400_BAD_REQUEST)


class PointViewSet(ModelViewSet):
    queryset = Point.objects.all()
    serializer_class = PointDefaultSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter]
    search_fields = ['code', 'name']
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

    @action(methods=['GET'], detail=False)
    def export(self, request):
        dataset = PointResource().export()
        return Response(dataset.csv, status=status.HTTP_200_OK)

    @action(methods=['POST'], detail=False)
    def _import(self, request):
        try:
            resource = PointResource()
            errors = []
            invalids = []
            if request.FILES:
                file = request.FILES['file']
                data_set = Dataset()
                data_set.load(file.read())
                result = resource.import_data(
                    data_set, dry_run=True)  # Test the data import
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
                result = resource.import_data(
                    data_set, dry_run=False)  # Actually import now
                return Response({
                    "totals": result.totals,
                    "total_rows": result.total_rows,
                }, status=status.HTTP_200_OK)
        except ValueError as e:
            return Response(e, status=status.HTTP_400_BAD_REQUEST)


class EquipmentToolsViewSet(ModelViewSet):
    queryset = EquipmentTools.objects.all()
    serializer_class = EquipmentToolsDefaultSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter]
    search_fields = ['serial', 'description', 'mark', 'model', 'year', 'license_plate']
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


class AccessGroupFilter(filters.FilterSet):
    persons = filters.CharFilter(method='filter_by_persons')
    name = filters.CharFilter(lookup_expr='icontains')
    description = filters.CharFilter(lookup_expr='icontains')
    persons__name = filters.CharFilter(lookup_expr='icontains')
    persons__last_name = filters.CharFilter(lookup_expr='icontains')
    persons__doc_ident = filters.CharFilter(lookup_expr='icontains')    

    def filter_by_persons(self, queryset, name, value):
        return queryset.filter(persons__in=value)

    class Meta:
        model = AccessGroup
        fields = ['name', 'description', 'persons', 'persons__name', 'persons__last_name', 'persons__doc_ident']


class AccessGroupViewSet(ModelViewSet):
    queryset = AccessGroup.objects.all()
    serializer_class = AccessGroupSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter]
    search_fields = ['name', 'description', 'persons__name', 'persons__last_name', 'persons__doc_ident']
    permission_classes = (AllowAny,)
    filterset_class = AccessGroupFilter

    def paginate_queryset(self, queryset):
        not_paginator = self.request.query_params.get('not_paginator', None)
        if self.paginator is None or not_paginator:
            return None
        return self.paginator.paginate_queryset(queryset, self.request, view=self)


class AccessEntryFilter(filters.FilterSet):
    persons = filters.CharFilter(method='filter_by_persons')
    title = filters.CharFilter(lookup_expr='icontains')
    description = filters.CharFilter(lookup_expr='icontains')
    persons__name = filters.CharFilter(lookup_expr='icontains')
    persons__last_name = filters.CharFilter(lookup_expr='icontains')
    persons__doc_ident = filters.CharFilter(lookup_expr='icontains')
    group = filters.CharFilter(lookup_expr='icontains')
    group__name = filters.CharFilter(lookup_expr='icontains')
    group__description = filters.CharFilter(lookup_expr='icontains')
    group__persons__name = filters.CharFilter(lookup_expr='icontains')
    group__persons__last_name = filters.CharFilter(lookup_expr='icontains')
    group__persons__doc_ident = filters.CharFilter(lookup_expr='icontains')
    date_start = filters.DateFilter(lookup_expr='icontains')
    date_end = filters.DateFilter(lookup_expr='icontains')
    week_days = filters.CharFilter(method='filter_by_week_days')
    access_type = filters.CharFilter(lookup_expr='icontains')
    access_type__in = filters.CharFilter(method='filter_by_access_type')
    min_date_start = filters.DateFilter(field_name='date_start', lookup_expr='gte')
    max_date_start = filters.DateFilter(field_name='date_start', lookup_expr='lte')
    min_date_end = filters.DateFilter(field_name='date_end', lookup_expr='gte')
    max_date_end = filters.DateFilter(field_name='date_end', lookup_expr='lte')
    min_start_time = filters.TimeFilter(field_name='start_time', lookup_expr='gte')
    max_start_time = filters.TimeFilter(field_name='start_time', lookup_expr='lte')
    min_end_time = filters.TimeFilter(field_name='end_time', lookup_expr='gte')
    max_end_time = filters.TimeFilter(field_name='end_time', lookup_expr='lte')

    min_date = filters.DateFilter(method='filter_by_min_date')
    max_date = filters.DateFilter(method='filter_by_max_date')
    persons_global = filters.CharFilter(method='filter_by_persons_global')
    
    def filter_by_persons(self, queryset, name, value):
        return queryset.filter(persons__in=value)

    def filter_by_week_days(self, queryset, name, value):
        return queryset.filter(week_days__in=value)

    def filter_by_access_type(self, queryset, name, value):
        return queryset.filter(access_type__in=value)

    def filter_by_min_date(self, queryset, name, value):
        return queryset.filter(date_start__gte=value)
    
    def filter_by_max_date(self, queryset, name, value):
        return queryset.filter(date_end__lte=value)

    def filter_by_persons_global(self, queryset, name, value):
        return queryset.filter(Q(persons__name__icontains=value) | Q(persons__last_name__icontains=value) | Q(persons__doc_ident__icontains=value)  )


    class Meta:
        model = AccessEntry
        fields = ['title', 'description', 'date_start', 'date_end', 'persons', 'persons__name', 'persons__last_name', 
        'persons__doc_ident', 'group', 'group__name', 'group__description', 'group__persons__name', 
        'group__persons__last_name', 'group__persons__doc_ident', 'week_days', 'access_type', 'access_type__in',
        'min_date_start', 'max_date_start', 'min_date_end', 'max_date_end', 'min_start_time', 'max_start_time', 'min_end_time', 'max_end_time',
        'min_date', 'max_date', 'persons_global']


class AccessEntryViewSet(ModelViewSet):
    queryset = AccessEntry.objects.all()
    serializer_class = AccessEntrySerializer
    filter_backends = [DjangoFilterBackend, SearchFilter]
    search_fields = ['title', 'description', 'persons__name', 'persons__last_name', 
    'persons__doc_ident', 'group__name', 'group__description', 'group__persons__name', 
    'group__persons__last_name', 'group__persons__doc_ident']
    
    permission_classes = (AllowAny,)
    filterset_class = AccessEntryFilter

    def paginate_queryset(self, queryset):
        not_paginator = self.request.query_params.get('not_paginator', None)
        if self.paginator is None or not_paginator:
            return None
        return self.paginator.paginate_queryset(queryset, self.request, view=self)