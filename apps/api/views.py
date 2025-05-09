from datetime import datetime
import json
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
from django.shortcuts import get_object_or_404
from apps.core.models import TypeNews
from apps.main.models import News, TypePerson
from rest_framework.exceptions import APIException
from django.conf import settings
from django.core.cache import cache


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
                'employee'
            ).order_by('-created')

            return Response(list(novelties))


class NoveltyByTypeAPI(SecureAPIView):
    """
    Endpoint que devuelve formatos diferentes según el tipo de novedad.
    Ejemplo: /api/novelties/accidente/ o /api/novelties/mantenimiento/
    """
    permission_classes = (AllowAny,)

    @staticmethod
    def parse_date(date_str):
        try:
            naive_date = datetime.strptime(date_str, '%Y-%m-%d')
            return make_aware(naive_date)
        except (ValueError, TypeError):
            raise InvalidDateException()
        
    @swagger_auto_schema(
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
            openapi.Parameter(
                'type_new',
                openapi.IN_PATH,
                type=openapi.TYPE_STRING,
                description="Código del tipo de novedad (ej: 'accidente', 'mantenimiento')"
            ),
        ],
        responses={
            200: openapi.Response(
                description="Novedades formateadas según tipo",
                schema=openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Schema(
                        type=openapi.TYPE_OBJECT,
                        properties={
                            'number': openapi.Schema(type=openapi.TYPE_INTEGER),
                            'created': openapi.Schema(type=openapi.TYPE_STRING),
                            'employee': openapi.Schema(type=openapi.TYPE_STRING),
                        }
                    )
                )
            )
        }
    )
    def get(self, request, type_new):
        # 1. Obtener el tipo de novedad
        response_data = []
        novelty_type = get_object_or_404(TypeNews, code=type_new)

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
            queryset = News.objects.filter(type_news_id=novelty_type.id)

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
                'employee',
                'info'
            ).order_by('-created')

            response_data = self._format_by_type(novelties, novelty_type.code)

        return Response(list(response_data))

    def _extract_attached_files(self, info_data):
        file_key = next((k for k in info_data if k.startswith('ATTACHED_FILE_')), None)
        return info_data.get(file_key, {}).get('attachedFiles') if file_key else None

    def _extract_vehicle_data(self, info_data):
        """
        Extrae y estructura los datos del vehículo del campo info,
        buscando cualquier clave que comience con 'VEHICLE'
        """
        # Buscar la clave que comienza con VEHICLE_
        vehicle_key = next(
            (key for key in info_data.keys() if key.startswith('VEHICLE_')),
            None
        )

        if not vehicle_key:
            return None

        vehicle_info = info_data[vehicle_key]

        # Estructura base
        vehicle_data = {
            'hora': vehicle_info.get('hour'),
            'tipo_movimiento': 'ENTRADA' if vehicle_info.get('movement_type') == 'employee' else 'SALIDA',
            'placa': vehicle_info.get('license_plate'),
            'modelo': vehicle_info.get('model'),
            'propietario': vehicle_info.get('owner_full_name')
        }

        # Datos específicos para vehículos de carga
        # cargo_data = vehicle_info.get('cargo_vehicle', None)

        # vehicle_data.update({
        #     'documento': cargo_data.get('document_number'),
        #     'precintado': cargo_data.get('sealed'),
        #     'numero_precinto': cargo_data.get('seal_number'),
        #     'placa_remolque': cargo_data.get('trailer_plate')
        # })

        vehicle_data['tipo_propietario'] = vehicle_info.get('owner_type', '').upper()


        # Materiales (si existen)
        # if 'materials' in vehicle_info:
        #     vehicle_data['materiales'] = vehicle_info['materials'].get('value', [])

        return vehicle_data

    def _get_person_types_map(self):
        """Obtiene todos los tipos de persona con cache"""
        cache_key = 'all_person_types'
        types = cache.get(cache_key)

        if not types:
            types = {
                str(tp.id): {
                    'descripcion': tp.description,
                    'prioridad': tp.priority,
                    'es_institucion': tp.is_institution,
                    'requiere_datos_empresa': tp.requires_company_data
                }
                for tp in TypePerson.objects.filter(is_active=True)
            }
            cache.set(cache_key, types, timeout=60 * 60 * 24)  # Cache por 24 horas
        return types

    def _extract_person_data(self, info_data):
        """
        Extrae y estructura datos de personas del campo info,
        buscando claves que comiencen con 'PERSON_'
        """
        persons = []
        type_map = self._get_person_types_map()

        # Buscar todas las claves de persona
        person_keys = [key for key in info_data.keys()
                       if key.startswith('PERSON_') and isinstance(info_data[key], dict)]

        for key in person_keys:
            person_info = info_data[key]

            type_person_id = person_info.get('type_person')
            type_data = type_map.get(type_person_id, {})

            # Datos base
            person_data = {
                'tipo_id': type_person_id,
                'tipo_descripcion': type_data.get('descripcion', 'Desconocido'),
                'nombre_completo': person_info.get('full_name'),
                'identificacion': person_info.get('identification_number'),
                'hora': person_info.get('hour'),
                'tipo_movimiento': 'ENTRADA' if person_info.get('movement_type') == 'employee' else 'SALIDA',
                'ingreso_material': 'SI' if person_info.get('entry') else 'NO',
                'razon_visita': person_info.get('reason_visit'),
                'lugar_recepcion': person_info.get('place_of_reception'),
                'numero_tarjeta': person_info.get('assigned_card_number'),
                'acompanantes': person_info.get('accompany_visitor'),
                'empresa': person_info.get('company_name', ''),
                'rif': person_info.get('rif', ''),
                'persona_autoriza': person_info.get('name_recibe', '').replace("-", ""),
                'identificacion_autoriza': person_info.get('ident_recibe', '').replace("-", ""),
                'cargo_autoriza': person_info.get('cargo_recibe', '').replace("-", ""),
                'numero_guia_factura': person_info.get('guide_number', ''),
                'instituccion': person_info.get('instituccion', '').replace("-", ""),
                'observacion': person_info.get('observacion', '').replace("-", ""),

            }

            persons.append(person_data)

        return persons

    def _format_by_type(self, queryset, type_code):
        """Transforma los datos según el tipo de novedad"""
        result = []

        for item in queryset:
            base_data = {
                'number': item['number'],
                'fecha': item['created']
            }

            # Procesamiento especial según el tipo
            info_data = json.loads(item.pop('info', {}))

            if type_code == '004':
                vehicle_data = self._extract_vehicle_data(info_data)
                if vehicle_data:
                    base_data.update(vehicle_data)

                # Agregar observaciones si existen
                free_text_key = next(
                    (key for key in info_data.keys() if key.startswith('FREE_TEXT_')),
                    None
                )
                if free_text_key:
                    base_data['observaciones'] = info_data[free_text_key]

            elif type_code == '006':  # Control de visitantes
                # Extraer datos de personas
                persons_data = self._extract_person_data(info_data)
                if persons_data:
                    base_data['personas'] = persons_data

                # Extraer selección (ej: SELECTION_2)
                selection_key = next(
                    (key for key in info_data.keys() if key.startswith('SELECTION_')),
                    None
                )
                if selection_key:
                    base_data['autorizacion'] = info_data[selection_key]

                # Extraer archivos adjuntos
                # attached_files = [
                #     info_data[key]['attachedFiles']
                #     for key in info_data.keys()
                #     if key.startswith('ATTACHED_FILE_') and info_data[key].get('attachedFiles')
                # ]
                # if attached_files:
                #     base_data['archivos_adjuntos'] = attached_files

            result.append(base_data)

        return result


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