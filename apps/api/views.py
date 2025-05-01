from datetime import datetime
from django.utils.timezone import make_aware
from drf_yasg2.utils import swagger_auto_schema
from drf_yasg2 import openapi
from rest_framework.views import APIView
from rest_framework.response import Response
from django_tenants.utils import tenant_context
from rest_framework.permissions import AllowAny
from apps.api.base_views import SecureAPIView
from apps.main.models import News
from rest_framework.exceptions import APIException


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

            novelties = queryset.values(
                'number',
                'created',
                'type_news__code',
                'type_news__description',
                'location__id',
                'location__code',
                'location__name',
                'employee'
            ).order_by('-created')

            return Response(list(novelties))