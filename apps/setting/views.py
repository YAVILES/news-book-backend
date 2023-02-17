import time
import json
import tablib
import requests
from django_celery_beat.models import PeriodicTask
from django_celery_results.models import TaskResult
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.filters import SearchFilter
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet
from tablib import Dataset
from django_filters import rest_framework as filters

from apps.main.models import News, Location, Material
from apps.main.serializers import NewsDefaultSerializer, MaterialScopeSerializer
from apps.setting.admin import NotificationResource
from apps.setting.models import Notification
from apps.setting.serializers import NotificationDefaultSerializer, TaskResultDefaultSerializer, \
    PeriodicTaskDefaultSerializer

from apps.setting.tasks import generate_notification_async, generate_notification_not_fulfilled

url_api_ibart = 'http://69.10.42.61/api-ibarti2'


class NotificationViewSet(ModelViewSet):
    queryset = Notification.objects.all()
    serializer_class = NotificationDefaultSerializer
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

    @action(methods=['POST'], detail=False)
    def my_task(self, request):
        _id = str(Notification.objects.last().id)
        generate_notification_not_fulfilled.delay(_id)
        return Response({}, status=status.HTTP_200_OK)

    @action(methods=['GET'], detail=False)
    def export(self, request):
        dataset = NotificationResource().export()
        return Response(dataset.csv, status=status.HTTP_200_OK)

    @action(methods=['POST'], detail=False)
    def _import(self, request):
        try:
            resource = NotificationResource()
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
                    for c in Notification._meta.get_field(field).choices:
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
                for c in Notification._meta.get_field(field).choices:
                    choices.append({
                        "value": c[0],
                        "description": c[1]
                    })
                return Response(choices, status=status.HTTP_200_OK)
            except ValueError as e:
                return Response(e, status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response({"error": "the field parameter is mandatory"}, status=status.HTTP_400_BAD_REQUEST)


class IbartiViewSet(viewsets.ViewSet):
    permission_classes = (AllowAny,)

    @action(methods=['GET'], detail=False)
    def planned_staff(self, request):
        if 'location' in request.headers and request.headers['location']:
            code_location = Location.objects.get(pk=request.headers['location']).code
        else:
            code_location = self.request.query_params.get('code_location', 157)

        hour = time.strftime('%H:%M', time.localtime())
        response = requests.get(
            url=url_api_ibart + "/manpower-planning/planned-staff",
            params={"location": code_location, "hour": hour}
        )
        if response.status_code == 200:
            return Response(response.json(), status=status.HTTP_200_OK)
        else:
            return Response(response.text, status=status.HTTP_400_BAD_REQUEST)

    @action(methods=['GET'], detail=False)
    def oesvica_staff(self, request):
        if 'location' in request.headers and request.headers['location']:
            code_location = Location.objects.get(pk=request.headers['location']).code
        else:
            code_location = self.request.query_params.get('code_location', 157)
        response = requests.get(
            url=url_api_ibart + "/manpower-planning/oesvica-staff",
            params={"location": code_location}
        )
        if response.status_code == 200:
            return Response(response.json(), status=status.HTTP_200_OK)
        else:
            return Response(response.text, status=status.HTTP_400_BAD_REQUEST)

    @action(methods=['GET'], detail=False)
    def former_guard(self, request):
        if 'location' in request.headers and request.headers['location']:
            code_location = Location.objects.get(pk=request.headers['location']).code
        else:
            code_location = self.request.query_params.get('code_location', None)
        data = NewsDefaultSerializer(
            News.objects.filter(
                location__code=code_location,
                type_news__is_changing_of_the_guard=True
            ).order_by('created').last(),
            context=self.get_serializer_context()
        ).data
        info = []
        if data['info']:
            info = json.loads(data['info'])
        result = []
        for key in info:
            if str(key).startswith('OESVICA_STAFF') or str(key).startswith('PLANNED_STAFF'):
                for trab in info[key]:
                    result.append({
                        "cod_ficha": trab.get("cod_ficha"),
                        "name_and_surname": trab.get("name_and_surname")
                    })
        return Response(result, status=status.HTTP_200_OK)

    @action(methods=['GET'], detail=False)
    def sub_line_scope(self, request):
        if 'location' in request.headers and request.headers['location']:
            code_location = Location.objects.get(pk=request.headers['location']).code
        else:
            code_location = self.request.query_params.get('code_location', 157)
        try:
            response = requests.get(
                url=url_api_ibart + "/inventory/scope",
                params={"location": code_location}
            )
        except Exception as e:
            return Response(e.__str__(), status=status.HTTP_400_BAD_REQUEST)

        if response.status_code == 200:
            scope = response.json()
            materials = MaterialScopeSerializer(Material.objects.all(), many=True).data
            data = scope + materials
            return Response(data, status=status.HTTP_200_OK)
        else:
            return Response(response.text, status=status.HTTP_400_BAD_REQUEST)

    @action(methods=['GET'], detail=False)
    def location_current(self, request):
        if 'location' in request.headers and request.headers['location']:
            code_location = Location.objects.get(pk=request.headers['location']).code
        else:
            code_location = self.request.query_params.get('code_location', 157)
        try:
            response = requests.get(
                url=url_api_ibart + "/client/location",
                params={"location": code_location}
            )
        except Exception as e:
            return Response(e.__str__(), status=status.HTTP_400_BAD_REQUEST)

        if response.status_code == 200:
            return Response(response.json(), status=status.HTTP_200_OK)
        else:
            return Response(response.text, status=status.HTTP_400_BAD_REQUEST)

    @action(methods=['GET'], detail=False)
    def valid_ficha(self, request):
        ficha = self.request.query_params.get('ficha', None)
        try:
            response = requests.get(
                url=url_api_ibart + "/ficha/get",
                params={"ficha": ficha}
            )
        except Exception as e:
            return Response(e.__str__(), status=status.HTTP_400_BAD_REQUEST)

        if response.status_code == 200:
            data = response.json()
            if not hasattr(data, 'error'):
                return Response(data, status=status.HTTP_200_OK)
            else:
                return Response(data, status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response(response.text, status=status.HTTP_400_BAD_REQUEST)


class TestEmailFilter(filters.FilterSet):
    email = filters.CharFilter()

    class Meta:
        fields = ['email']


class TestEmailView(APIView):
    permission_classes = (AllowAny,)
    authentication_classes = []
    filter_backends = [DjangoFilterBackend]
    filterset_class = TestEmailFilter

    def get(self, request):
        email_user = self.request.query_params.get('email', None)
        if email_user:
            try:
                new = News.objects.last()
                generate_notification_async.delay(new.id)
                '''
                email = EmailMultiAlternatives(
                    'EMAIL TEST',
                    "TEST" + str(datetime.hour) + ":" + str(datetime.minute) + str(datetime.today()),
                    settings.EMAIL_HOST_USER,
                    [email_user]
                )
                email.send()
                '''
            except ValueError as e:
                return Response(
                    {"error": e, "msg": "No se pudo enviar"},
                    status=status.HTTP_400_BAD_REQUEST
                )
        else:
            return Response(
                {"msg": "El parametro email es obligatorio"},
                status=status.HTTP_400_BAD_REQUEST
            )

        return Response({
            "email": email_user
        }, status=status.HTTP_200_OK)


class TaskResultFilter(filters.FilterSet):
    module = filters.CharFilter(method="get_module")

    class Meta:
        model = TaskResult
        fields = ['id', 'task_name', 'status', 'result']

    def get_module(self, queryset, name, value):
        if value:
            return queryset.filter(accounts__mobile_payment_applies=True)
        return queryset


class TaskResultViewSet(ModelViewSet):
    queryset = TaskResult.objects.all()
    serializer_class = TaskResultDefaultSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_class = TaskResultFilter
    search_fields = ['id', 'task_name', 'status']
    authentication_classes = []
    permission_classes = (AllowAny, )

    def paginate_queryset(self, queryset):
        """
        Return a single page of results, or `None` if pagination is disabled.
        """
        not_paginator = self.request.query_params.get('not_paginator', None)

        if not_paginator:
            return None
        return self.paginator.paginate_queryset(queryset, self.request, view=self)

    @action(methods=['GET'], detail=False)
    def field_options(self, request):
        field = self.request.query_params.get('field', None)
        fields = self.request.query_params.getlist('fields', None)
        if fields:
            try:
                data = {}
                for field in fields:
                    data[field] = []
                    for c in TaskResult._meta.get_field(field).choices:
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
                for c in TaskResult._meta.get_field(field).choices:
                    choices.append({
                        "value": c[0],
                        "description": c[1]
                    })
                return Response(choices, status=status.HTTP_200_OK)
            except ValueError as e:
                return Response(e, status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response({"error": "the field parameter is mandatory"}, status=status.HTTP_400_BAD_REQUEST)


class PeriodicTaskViewSet(ModelViewSet):
    queryset = PeriodicTask.objects.all()
    serializer_class = PeriodicTaskDefaultSerializer
