from datetime import datetime
from django.utils.timezone import make_aware
from drf_yasg2.utils import swagger_auto_schema
from drf_yasg2 import openapi
from rest_framework.views import APIView
from rest_framework.response import Response
from django_tenants.utils import tenant_context
from django_tenants.utils import get_tenant_model, get_public_schema_name
from django.db import connection
from rest_framework.permissions import AllowAny
from apps.api.base_views import SecureAPIView
from apps.main.models import News
from rest_framework.exceptions import APIException
from django.conf import settings


class InvalidDateException(APIException):
    status_code = 400
    default_detail = 'Formato de fecha inválido. Use YYYY-MM-DD'
    default_code = 'invalid_date'


class NoveltiesAPI(SecureAPIView):
    """Devuelve novedades filtradas por tenant."""
    permission_classes = (AllowAny,)

    @staticmethod
    def parse_date(date_str):
        try:
            naive_date = datetime.strptime(date_str, '%Y-%m-%d')
            return make_aware(naive_date)
        except (ValueError, TypeError):
            raise InvalidDateException()

    @swagger_auto_schema(
        operation_description="Lista de novedades filtradas filtradas por cliente",
        manual_parameters=[
            openapi.Parameter(
                'X-API-Token',
                openapi.IN_HEADER,
                type=openapi.TYPE_STRING,
                required=True,
                description="Token de autenticación",
            ),
            openapi.Parameter(
                'X-Dts-Schema',
                openapi.IN_HEADER,
                type=openapi.TYPE_STRING,
                required=False,
                description="Schema del tenant (opcional para super tokens)",
            ),
            openapi.Parameter(
                'date_from',
                openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                format='date',
                description="Fecha inicial (YYYY-MM-DD)"
            ),
            openapi.Parameter(
                'date_to',
                openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                format='date',
                description="Fecha final (YYYY-MM-DD)"
            ),
        ],
        responses={
            200: openapi.Response(
                description="Lista de novedades",
                schema=openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Schema(
                        type=openapi.TYPE_OBJECT,
                        properties={
                            'number': openapi.Schema(type=openapi.TYPE_INTEGER),
                            'created': openapi.Schema(type=openapi.TYPE_STRING, format='date-time'),
                            'type_news__code': openapi.Schema(type=openapi.TYPE_STRING),
                            'type_news__description': openapi.Schema(type=openapi.TYPE_STRING),
                            'location__id': openapi.Schema(type=openapi.TYPE_INTEGER),
                            'location__code': openapi.Schema(type=openapi.TYPE_STRING),
                            'location__name': openapi.Schema(type=openapi.TYPE_STRING),
                            'employee': openapi.Schema(type=openapi.TYPE_STRING),
                        }
                    )
                )
            ),
            400: "Fecha inválida",
            403: "Acceso no autorizado"
        }
    )
    def get(self, request):
        # Procesamiento de fechas con timezone
        date_from = None
        date_to = None

        if 'date_from' in request.GET:
            date_from = self.parse_date(request.GET['date_from'])

        if 'date_to' in request.GET:
            date_to = self.parse_date(request.GET['date_to'])

        # Validación de fechas
        if date_from and date_to and date_from > date_to:
            raise InvalidDateException("La fecha inicial no puede ser mayor que la final")

        with tenant_context(request.tenant):
            queryset = News.objects.select_related('type_news', 'location')

            if date_from:
                queryset = queryset.filter(created__gte=date_from)

            if date_to:
                queryset = queryset.filter(created__lte=date_to)

            to_char = f'TO_CHAR(main_news.created AT TIME ZONE \'{settings.TIME_ZONE}\', \'YYYY-MM-DD HH24:MI\')'
            novelties = queryset.extra(
                select={'created': to_char}
            ).values(
                'number',
                'created',
                'type_news__code',
                'type_news__description',
                'location__id',
                'location__code',
                'location__name',
                'employee',
                'info'
            ).order_by('-created')

            return Response(list(novelties))


class TypeNewsAPI(SecureAPIView):
    """Devuelve todos los tipos de novedades disponibles."""
    permission_classes = (AllowAny,)

    @swagger_auto_schema(
        operation_description="Lista de todos los tipos de novedades disponibles",
        manual_parameters=[
            openapi.Parameter(
                'X-API-Token',
                openapi.IN_HEADER,
                type=openapi.TYPE_STRING,
                required=True,
                description="Token de autenticación",
            ),
            openapi.Parameter(
                'X-Dts-Schema',
                openapi.IN_HEADER,
                type=openapi.TYPE_STRING,
                required=False,
                description="Schema del tenant (opcional para super tokens)",
            ),
        ],
        responses={
            200: openapi.Response(
                description="Lista de tipos de novedades",
                schema=openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Schema(
                        type=openapi.TYPE_OBJECT,
                        properties={
                            'code': openapi.Schema(type=openapi.TYPE_STRING),
                            'description': openapi.Schema(type=openapi.TYPE_STRING),
                            'is_active': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                            'is_changing_of_the_guard': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                        }
                    )
                )
            ),
            403: "Acceso no autorizado"
        }
    )
    def get(self, request):
        with tenant_context(request.tenant):
            if request.tenant:
                queryset = request.tenant.type_news.all()
            else:
                queryset = TypeNews.objects.all()

            types = queryset.values(
                'code',
                'description',
                'is_active',
                'is_changing_of_the_guard'
            ).order_by('description')

            return Response(list(types))


class ClientsAPI(SecureAPIView):
    """Devuelve la lista de clientes (tenants) disponibles."""
    permission_classes = (AllowAny,)

    @swagger_auto_schema(
        operation_description="Lista de clientes (tenants) disponibles",
        manual_parameters=[
            openapi.Parameter(
                'X-API-Token',
                openapi.IN_HEADER,
                type=openapi.TYPE_STRING,
                required=True,
                description="Token de autenticación",
            ),
        ],
        responses={
            200: openapi.Response(
                description="Lista de clients",
                schema=openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Schema(
                        type=openapi.TYPE_OBJECT,
                        properties={
                            'schema_name': openapi.Schema(type=openapi.TYPE_STRING),
                            'name': openapi.Schema(type=openapi.TYPE_STRING),
                            'email': openapi.Schema(type=openapi.TYPE_STRING),
                            'created_on': openapi.Schema(type=openapi.TYPE_STRING, format='date')
                        }
                    )
                )
            ),
            403: "Acceso no autorizado"
        }
    )
    def get(self, request):
        # Solo para super tokens con acceso completo
        if not request.api_consumer.has_full_access:
            return Response(
                {'error': 'Se requiere token con acceso completo para esta operación'},
                status=403
            )

        # Conexión directa al schema public
        original_schema = connection.schema_name
        try:
            connection.set_schema(get_public_schema_name())
            Client = get_tenant_model()
            clients = Client.objects.all().exclude(schema_name='public').values(
                'schema_name',
                'name',
                'email',
                'created_on'
            ).order_by('name')

            return Response(list(clients))

        finally:
            # Restaurar schema original
            connection.set_schema(original_schema)