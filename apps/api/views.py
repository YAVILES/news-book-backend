from datetime import datetime
import json
import re
import pytz
from apps.setting.models import FacialRecognitionEvent
from django.utils.timezone import make_aware
from drf_yasg2.utils import swagger_auto_schema
from drf_yasg2 import openapi
from rest_framework.response import Response
from rest_framework.parsers import JSONParser, MultiPartParser, FormParser
from django_tenants.utils import tenant_context
from django_tenants.utils import get_tenant_model, get_public_schema_name
from django.db import connection
from rest_framework.permissions import AllowAny
from apps.api.base_views import SecureAPIView
from django.shortcuts import get_object_or_404
from apps.core.models import TypeNews
from apps.main.models import News, TypePerson, Location
from rest_framework.exceptions import APIException
from rest_framework.views import APIView
from django.conf import settings
from django.core.cache import cache
from rest_framework import status
from datetime import datetime
import pytz
from django.utils.timezone import make_aware
from django.core.exceptions import ValidationError
from .parsers import MixedReplaceParser


LOG_FILE = "facial_recognition.log"


def write_to_log(request_data, schema_name=None):
    """
    Guarda todos los datos recibidos en el log, incluyendo parámetros y cuerpo de la petición

    Args:
        request_data (dict): Datos del cuerpo de la petición (request.data)
        cliente (str, optional): Parámetro de URL 'cliente'. Defaults to None.
        ubicacion (str, optional): Parámetro de URL 'ubicacion'. Defaults to None.
    """
    log_data = {
        'timestamp': datetime.now().isoformat(),
        'request_data': request_data,
        'url_params': {
            'cliente': schema_name
        },
        # 'full_data': {
        #     **request_data,
        #     'cliente': schema_name
        # }
    }

    # Aquí implementa tu lógica para guardar el log (archivo, base de datos, etc.)
    # Ejemplo básico guardando en un archivo JSON:
    import json
    with open('facial_recognition_logs.json', 'a') as f:
        f.write(json.dumps(log_data) + '\n')

def get_person_types_map():
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


class InvalidDateException(APIException):
    status_code = 400
    default_detail = 'Formato de fecha inválido. Use YYYY-MM-DD'
    default_code = 'invalid_date'


class TypePersonAPI(SecureAPIView):
    """Devuelve novedades filtradas por tenant."""
    permission_classes = (AllowAny,)

    @swagger_auto_schema(
        operation_description="Lista de tipos de personas filtradas filtradas por cliente",
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
                description="Schema del tenant",
            )
        ],
        responses={
            200: openapi.Response(
                description="Lista de tipo de personas",
                schema=openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Schema(
                        type=openapi.TYPE_OBJECT,
                        properties={
                            'id': openapi.Schema(type=openapi.TYPE_STRING),
                            'description': openapi.Schema(type=openapi.TYPE_STRING),
                            'priority': openapi.Schema(type=openapi.TYPE_STRING),
                            'is_active': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                            'is_institution': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                            'requires_company_data': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                            'requires_guide_number': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                        }
                    )
                )
            ),
            403: "Acceso no autorizado"
        }
    )
    def get(self, request):
        with tenant_context(request.tenant):
            queryset = TypePerson.objects.all().values(
                'id',
                'description',
                'priority',
                'is_active',
                'is_institution',
                'requires_company_data',
                'requires_guide_number'
            )

        return Response(list(queryset))


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
                'info',
                'template'
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

    def _extract_person_data(self, info_data):
        """
        Extrae y estructura datos de personas del campo info,
        buscando claves que comiencen con 'PERSON_'
        """
        persons = []
        type_map = get_person_types_map()

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

        # Mapeo de condiciones de salud
        HEALTH_CONDITIONS = {
            'good': 'Buena',
            'average': 'Regular',
            'bad': 'Mala',
            'not_in_service': 'No se encuentra en el servicio'
        }

        for item in queryset:
            base_data = {
                'number': item['number'],
                'fecha': item['created'],
                'empleado': item['employee']
            }

            # Procesamiento especial según el tipo
            info_data = json.loads(item.pop('info', {}))
            template_data = json.loads(item.get('template', '[]'))

            if type_code == '001':  # Cambio de guardia
                processed_data = {}
                field_mapping = {}

                # Primero creamos un mapeo de los campos basado en el template
                for field in template_data:
                    if field['code'] in ['SELECTION', 'FREE_TEXT']:
                        # Buscamos el campo correspondiente en info_data
                        for key in info_data.keys():
                            if key.startswith(field['code'] + '_'):
                                label = field.get('label', '').lower().replace(' ', '_')
                                if label:
                                    field_mapping[key] = label
                                else:
                                    # Si no hay label, usamos el código como último recurso
                                    field_mapping[key] = field['code'].lower()

                # Procesamos los campos mapeados
                for key, value in info_data.items():
                    if key in field_mapping:
                        processed_data[field_mapping[key]] = value
                    elif key.startswith('PLANNED_STAFF_'):
                        if 'personal_recibe' not in processed_data:
                            processed_data['personal_recibe'] = value
                        elif 'personal_disponible_dia_libre' not in processed_data:
                            processed_data['personal_disponible_dia_libre'] = value
                        elif 'personal_faltante' not in processed_data:
                            processed_data['personal_faltante'] = value
                    elif key.startswith('OESVICA_STAFF_'):
                        processed_data['personal_no_planificado'] = value
                    elif key.startswith('FORMER_GUARD_'):
                        processed_data['personal_entrega'] = value
                    elif key.startswith('ATTACHED_FILE_'):
                        attached_files = self._extract_attached_files(info_data)
                        if attached_files:
                            processed_data['archivos_adjuntos'] = attached_files
                    elif key.startswith('ERRATA_'):
                        processed_data['erratas'] = value

                base_data.update(processed_data)

            elif type_code == '002':  # Materiales de Trabajo
                processed_data = {
                    'materiales_oesvica': [],
                    'materiales_cliente': [],
                    'archivos_adjuntos': []
                }

                # 1. Procesar materiales de Oesvica (SUB_LINE_1)
                if 'SUB_LINE_1' in info_data:
                    for material in info_data['SUB_LINE_1']:
                        processed_data['materiales_oesvica'].append({
                            'codigo': material.get('code'),
                            'item': material.get('item'),
                            'nombre': material.get('name'),
                            'cantidad': material.get('amount', 0),
                            'observacion': material.get('observation', ''),
                            'condicion': {
                                'codigo': material.get('health_condition'),
                                'descripcion': HEALTH_CONDITIONS.get(
                                    material.get('health_condition'),
                                    'Desconocida'
                                )
                            }
                        })

                # 2. Procesar materiales del cliente (SUB_LINE_3)
                if 'SUB_LINE_3' in info_data:
                    for material in info_data['SUB_LINE_3']:
                        processed_data['materiales_cliente'].append({
                            'codigo': material.get('code'),
                            'item': material.get('item'),
                            'nombre': material.get('name'),
                            'cantidad': material.get('amount', 0),
                            'observacion': material.get('observation', ''),
                            'condicion': {
                                'codigo': material.get('health_condition'),
                                'descripcion': HEALTH_CONDITIONS.get(
                                    material.get('health_condition'),
                                    'Desconocida'
                                )
                            }
                        })

                # 3. Procesar archivos adjuntos (ATTACHED_FILE_4)
                # if 'ATTACHED_FILE_4' in info_data:
                #     files = info_data['ATTACHED_FILE_4'].get('attachedFiles')
                #     if files:
                #         processed_data['archivos_adjuntos'] = files

                # 4. Procesar erratas (ERRATA_5)
                if 'ERRATA_5' in info_data:
                    processed_data['erratas'] = {
                        'editado': info_data['ERRATA_5'].get('edited', False),
                        'observacion': info_data['ERRATA_5'].get('observation_errata', '')
                    }

                # Limpieza de campos vacíos
                if not processed_data['materiales_oesvica']:
                    del processed_data['materiales_oesvica']
                if not processed_data['materiales_cliente']:
                    del processed_data['materiales_cliente']
                if not processed_data['archivos_adjuntos']:
                    del processed_data['archivos_adjuntos']
                if not processed_data.get('erratas', {}).get('observacion'):
                    processed_data.pop('erratas', None)

                base_data.update(processed_data)

            elif type_code == '003':  # Rondas Perimetrales
                processed_data = {
                    'ronda': {},
                    'personal': [],
                    'archivos_adjuntos': []
                }

                # 1. Procesar datos de la ronda (ROUND_)
                for key in info_data:
                    if key.startswith('ROUND_'):
                        round_data = info_data[key]
                        processed_data['ronda'] = {
                            'numero': round_data.get('number'),
                            'hora_inicio': round_data.get('hour_start'),
                            'hora_fin': round_data.get('hour_end'),
                            'observaciones': round_data.get('observation')
                        }

                # 2. Procesar personal (PLANNED_STAFF_)
                for key in info_data:
                    if key.startswith('PLANNED_STAFF_'):
                        for member in info_data[key]:
                            processed_data['personal'].append({
                                'nombre': member.get('name_and_surname'),
                                'codigo_ficha': member.get('cod_ficha'),
                                'telefono': member.get('telefono'),
                                # 'estado': member.get('guard_status'),
                                # 'condicion_salud': HEALTH_CONDITIONS.get(member.get('health_condition', ''), 'Desconocida')
                            })

                # 3. Procesar archivos adjuntos (ATTACHED_FILE_)
                # for key in info_data:
                #     if key.startswith('ATTACHED_FILE_'):
                #         files = info_data[key].get('attachedFiles')
                #         if files:
                #             processed_data['archivos_adjuntos'].extend(files)

                # 4. Procesar erratas (ERRATA_)
                for key in info_data:
                    if key.startswith('ERRATA_'):
                        processed_data['erratas'] = {
                            'editado': info_data[key].get('edited', False),
                            'observacion': info_data[key].get('observation_errata', '')
                        }
                        break

                # Limpieza de campos vacíos
                if not processed_data['personal']:
                    del processed_data['personal']
                if not processed_data['archivos_adjuntos']:
                    del processed_data['archivos_adjuntos']
                if not processed_data.get('erratas', {}).get('observacion'):
                    processed_data.pop('erratas', None)

                base_data.update(processed_data)

            elif type_code == '004':
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

            elif type_code == '005':  # Registro Entrada/Salida Empleados Coca-Cola
                processed_data = {
                    'empleados': [],
                    'autorizador': None,
                    'archivos_adjuntos': []
                }

                person_keys = [k for k in info_data if k.startswith('PERSON')]

                for index, key in enumerate(person_keys):
                    person_info = info_data[key]

                    # Detección del autorizador (no tiene type_person)
                    # Solo se registra como autorizador si es el último elemento
                    if index == len(person_keys) - 1:
                        processed_data['autorizador'] = {
                            'nombre': person_info.get('full_name', '').strip(),
                            'identificacion': person_info.get('identification_number')
                        }
                    else:
                        # Es una persona normal
                        processed_data['empleados'].append({
                            'nombre_completo': person_info.get('full_name', '').strip(),
                            'identificacion': person_info.get('identification_number'),
                            'hora': person_info.get('hour'),
                            'tipo_movimiento': 'ENTRADA' if person_info.get('entry') else 'SALIDA',
                            'razon_visita': person_info.get('reason_visit'),
                            'numero_tarjeta': person_info.get('assigned_card_number'),
                            'observaciones': person_info.get('observacion', '')
                        })
                        
                # Procesar archivos adjuntos (ATTACHED_FILE_4)
                # if 'ATTACHED_FILE_4' in info_data:
                #     files = info_data['ATTACHED_FILE_4'].get('attachedFiles')
                #     if files:
                #         processed_data['archivos_adjuntos'] = files

                # Procesar erratas (ERRATA_5)
                if 'ERRATA_5' in info_data:
                    processed_data['erratas'] = {
                        'editado': info_data['ERRATA_5'].get('edited', False),
                        'observacion': info_data['ERRATA_5'].get('observation_errata', '')
                    }

                # Limpieza de campos vacíos
                if not processed_data['empleados']:
                    del processed_data['empleados']
                if not processed_data['archivos_adjuntos']:
                    del processed_data['archivos_adjuntos']
                if processed_data.get('autorizador') and not processed_data['autorizador'].get('nombre'):
                    del processed_data['autorizador']
                if not processed_data.get('erratas', {}).get('observacion'):
                    processed_data.pop('erratas', None)

                base_data.update(processed_data)

            elif type_code == '006':  # Control de visitantes
                processed_data = {
                    'personas': [],
                    'personas_adicionales': [],
                    'autorizador': None,
                    'archivos_adjuntos': []
                }
                type_map = get_person_types_map()

                # Primero procesamos todas las PERSON
                person_keys = [k for k in info_data if k.startswith('PERSON_')]

                tipo_descripcion = 'N/A'
                tipo_movimiento = ''
                razon_visita = ''

                for key in person_keys:
                    person_info = info_data[key]

                    # Detección del autorizador (no tiene type_person)
                    if not person_info.get('type_person'):
                        processed_data['autorizador'] = {
                            'nombre': person_info.get('full_name'),
                            'identificacion': person_info.get('identification_number')
                        }
                    else:
                        # Es una persona normal
                        type_person_id = person_info.get('type_person')
                        type_data = type_map.get(type_person_id, {})

                        tipo_descripcion = type_data.get('descripcion', 'Desconocido')
                        tipo_movimiento = 'ENTRADA' if person_info.get('movement_type') == 'employee' else 'SALIDA'
                        razon_visita = person_info.get('reason_visit')

                        processed_data['personas'].append({
                            'tipo_id': type_person_id,
                            'tipo_descripcion': tipo_descripcion,
                            'nombre_completo': person_info.get('full_name'),
                            'identificacion': person_info.get('identification_number'),
                            'hora': person_info.get('hour'),
                            'tipo_movimiento': tipo_movimiento,
                            'razon_visita': razon_visita,
                            'lugar_recepcion': person_info.get('place_of_reception'),
                            'numero_tarjeta': person_info.get('assigned_card_number'),
                            'fue_acompanado_por_oficial': person_info.get('accompany_visitor', 0),
                            'empresa': person_info.get('company_name', ''),
                            'rif': person_info.get('rif', '')
                        })

                # Procesamos campos adicionales
                for field in template_data:
                    field_code = field.get('code')

                    # Campos SELECTION
                    if field_code == 'SELECTION':
                        for key in info_data:
                            if key.startswith('SELECTION_'):
                                label = field.get('label', '').lower().replace(' ', '_')
                                if label:
                                    processed_data[label] = info_data[key]
                                break

                    # Campos PERSONS (personas adicionales)
                    elif field_code == 'PERSONS':
                        for key in info_data:
                            if key.startswith('PERSONS_'):
                                for person in info_data[key]:
                                    processed_data['personas_adicionales'].append({
                                        'identificacion': person.get('identification_number'),
                                        'nombre': person.get('full_name'),
                                        'numero_tarjeta': person.get('assigned_card_number'),
                                        'tipo_descripcion': tipo_descripcion,
                                        'tipo_movimiento': tipo_movimiento,
                                        'razon_visita': razon_visita,
                                    })

                    # Campos ATTACHED_FILE
                    # elif field_code == 'ATTACHED_FILE':
                    #     for key in info_data:
                    #         if key.startswith('ATTACHED_FILE_'):
                    #             files = info_data[key].get('attachedFiles', [])
                    #             if files:
                    #                 processed_data['archivos_adjuntos'].extend(files)

                    # Campos ERRATA
                    elif field_code == 'ERRATA':
                        for key in info_data:
                            if key.startswith('ERRATA_'):
                                processed_data['erratas'] = {
                                    'editado': info_data[key].get('edited', False),
                                    'observacion': info_data[key].get('observation_errata', '')
                                }
                                break

                # Limpieza de campos vacíos
                if not processed_data['personas']:
                    del processed_data['personas']
                if not processed_data['personas_adicionales']:
                    del processed_data['personas_adicionales']
                if not processed_data['archivos_adjuntos']:
                    del processed_data['archivos_adjuntos']
                if processed_data['autorizador'] is None:
                    del processed_data['autorizador']

                base_data.update(processed_data)

            elif type_code == '007':  # Reporte de Entrada y Salida de Activos
                processed_data = {
                    'tipo_activo': None,
                    'descripcion_activo': None,
                    'unidades_empaque': [],
                    'motivo': None,
                    'condicion_activo': None,
                    'cantidad_total': None,
                    'persona': None,
                    'autorizador': None,
                    'archivos_adjuntos': []
                }

                # Extraer datos básicos del formulario
                if 'SELECTION_2' in info_data:
                    processed_data['tipo_activo'] = info_data['SELECTION_2']

                if 'FREE_TEXT_3' in info_data:
                    processed_data['descripcion_activo'] = info_data['FREE_TEXT_3']

                if 'FREE_TEXT_11' in info_data:
                    processed_data['motivo'] = info_data['FREE_TEXT_11']

                if 'SELECTION_12' in info_data:
                    processed_data['condicion_activo'] = info_data['SELECTION_12']

                if 'AMOUNT_13' in info_data:
                    processed_data['cantidad_total'] = info_data['AMOUNT_13']

                # Procesar unidades de empaque
                empaque_mapping = {
                    'SELECTION_5': 'AMOUNT_8',  # Unidad 1 (Cajas) -> Cantidad
                    'SELECTION_7': 'AMOUNT_10',  # Unidad 2 (Paletas) -> Cantidad
                    'SELECTION_9': 'AMOUNT_13'  # Unidad 3 -> Cantidad
                }

                for unit_key, amount_key in empaque_mapping.items():
                    if unit_key in info_data and info_data[unit_key] and amount_key in info_data and info_data[
                        amount_key]:
                        processed_data['unidades_empaque'].append({
                            'tipo': info_data[unit_key],
                            'cantidad': info_data[amount_key]
                        })

                # Procesar persona (transportista/empleado)
                person_keys = [k for k in info_data if k.startswith('PERSON_')]

                # La primera persona es generalmente el transportista/empleado
                if len(person_keys) > 0:
                    person_info = info_data[person_keys[0]]
                    processed_data['persona'] = {
                        'nombre_completo': person_info.get('full_name', '').strip(),
                        'identificacion': person_info.get('identification_number'),
                        'empresa': person_info.get('company_name', ''),
                        'rif': person_info.get('rif', ''),
                        'hora': person_info.get('hour', ''),
                        'numero_guia': person_info.get('guide_number', ''),
                        'tipo_movimiento': 'ENTRADA' if person_info.get('entry', False) else 'SALIDA'
                    }

                # La segunda persona (si existe) es generalmente el autorizador
                if len(person_keys) > 1:
                    autorizador_info = info_data[person_keys[1]]
                    processed_data['autorizador'] = {
                        'nombre_completo': autorizador_info.get('full_name', '').strip(),
                        'identificacion': autorizador_info.get('identification_number', '')
                    }

                # Procesar archivos adjuntos
                # attached_file_key = next((k for k in info_data if k.startswith('ATTACHED_FILE_')), None)
                # if attached_file_key:
                #     attached_files = self._extract_attached_files(info_data)
                #     if attached_files:
                #         processed_data['archivos_adjuntos'] = attached_files

                # Procesar erratas
                if 'ERRATA_17' in info_data:
                    processed_data['erratas'] = {
                        'editado': info_data['ERRATA_17'].get('edited', False),
                        'observacion': info_data['ERRATA_17'].get('observation_errata', '')
                    }

                # Limpieza de campos vacíos
                if not processed_data['unidades_empaque']:
                    del processed_data['unidades_empaque']
                if not processed_data['archivos_adjuntos']:
                    del processed_data['archivos_adjuntos']
                if not processed_data.get('erratas', {}).get('observacion'):
                    processed_data.pop('erratas', None)

                base_data.update(processed_data)

            elif type_code == '0010':  # Novedad Importante
                processed_data = {
                    'descripcion': None,
                    'fecha': None,
                    'hora': None,
                    'personal_involucrado': [],
                    'archivos_adjuntos': []
                }

                # Extraer datos básicos del formulario
                if 'FREE_TEXT_1' in info_data:
                    processed_data['descripcion'] = info_data['FREE_TEXT_1']

                if 'DATE_2' in info_data and info_data['DATE_2']:
                    try:
                        # Convertir fecha a formato estándar si existe
                        processed_data['fecha'] = self.parse_date(info_data['DATE_2']).strftime('%Y-%m-%d')
                    except (ValueError, TypeError):
                        processed_data['fecha'] = info_data[
                            'DATE_2']  # Conservar el valor original si no se puede parsear

                if 'HOUR_3' in info_data:
                    processed_data['hora'] = info_data['HOUR_3']

                # Procesar personal de OESVICA involucrado
                if 'OESVICA_STAFF_4' in info_data and isinstance(info_data['OESVICA_STAFF_4'], list):
                    for miembro in info_data['OESVICA_STAFF_4']:
                        if isinstance(miembro, dict):  # Validación adicional por seguridad
                            processed_data['personal_involucrado'].append({
                                'nombre': miembro.get('name_and_surname', '').strip(),
                                'codigo_ficha': miembro.get('cod_ficha', ''),
                                'telefono': miembro.get('telefono', '')
                            })

                # Procesar archivos adjuntos
                # attached_file_key = next((k for k in info_data if k.startswith('ATTACHED_FILE_')), None)
                # if attached_file_key and info_data[attached_file_key].get('attachedFiles'):
                #     processed_data['archivos_adjuntos'] = info_data[attached_file_key]['attachedFiles']

                # Procesar erratas si existen
                if 'ERRATA_6' in info_data:
                    processed_data['erratas'] = {
                        'editado': info_data['ERRATA_6'].get('edited', False),
                        'observacion': info_data['ERRATA_6'].get('observation_errata', '')
                    }

                # Limpieza de campos vacíos
                if not processed_data['personal_involucrado']:
                    del processed_data['personal_involucrado']
                if not processed_data['archivos_adjuntos']:
                    del processed_data['archivos_adjuntos']
                if not processed_data.get('erratas', {}).get('observacion'):
                    processed_data.pop('erratas', None)
                if not processed_data['fecha']:
                    del processed_data['fecha']

                base_data.update(processed_data)

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


class InvalidFacialRecognitionData(APIException):
    status_code = 400
    default_detail = 'Datos de reconocimiento facial inválidos'
    default_code = 'invalid_facial_data'



class FacialRecognitionAPI(APIView):
    permission_classes = (AllowAny,)
    parser_classes = [MixedReplaceParser, JSONParser]

    @swagger_auto_schema(
        operation_description="Recibe eventos de reconocimiento facial desde dispositivos. "
                              "Soporta JSON directo (Content-Type: application/json) o "
                              "contenido embebido en multipart/x-mixed-replace.",
        manual_parameters=[
            openapi.Parameter(
                name='schema_name',
                in_=openapi.IN_PATH,
                description='Nombre del tenant (esquema de base de datos)',
                type=openapi.TYPE_STRING,
                required=True
            ),
            openapi.Parameter(
                name='location',
                in_=openapi.IN_PATH,
                description='Nombre del libro (ubicacion del cliente)',
                type=openapi.TYPE_STRING,
                required=True
            ),
            openapi.Parameter(
                name='movement_type',
                in_=openapi.IN_PATH,
                description='Nombre del tipo de movimiento (IN=Entrada, OUT=Salida)',
                type=openapi.TYPE_STRING,
                required=True
            )
        ],
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["Events"],
            properties={
                "Events": openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Items(type=openapi.TYPE_OBJECT, properties={
                        "Code": openapi.Schema(type=openapi.TYPE_STRING, example="AccessControl"),
                        "Data": openapi.Schema(type=openapi.TYPE_OBJECT, properties={
                            "UserID": openapi.Schema(type=openapi.TYPE_STRING, example="001875"),
                            "CreateTime": openapi.Schema(
                                type=openapi.TYPE_STRING,
                                format="date-time",
                                example="2025-07-17T12:54:47-04:30"
                            ),
                        }),
                    }),
                ),
            }
        ),
        responses={
            200: openapi.Response(description="Evento registrado exitosamente"),
            400: openapi.Response(description="Error de validación o datos inválidos"),
            500: openapi.Response(description="Error interno del servidor"),
        }
    )
    def post(self, request, schema_name=None, location=None, movement_type=None):
        data = None  # Inicializa data como None por defecto
        try:
            content_type = request.META.get("CONTENT_TYPE", "").lower()
            raw_bytes = getattr(request, 'body', b'')
            raw_body = raw_bytes.decode('utf-8', errors='ignore')

            if "multipart/x-mixed-replace" in content_type or "text/plain" in content_type:
                try:
                    # 1. Encontrar la parte que contiene el JSON
                    json_part = None
                    parts = raw_body.split('--myboundary')

                    for part in parts:
                        if 'Content-Type: text/plain' in part:
                            # 2. Extraer el contenido después de los headers
                            payload = part.split('\n\n', 1)[-1].strip()

                            # 3. Buscar el JSON completo entre el primer { y último }
                            json_start = payload.find('{')
                            json_end = payload.rfind('}') + 1

                            if json_start != -1 and json_end > json_start:
                                json_part = payload[json_start:json_end]
                                break

                    if not json_part:
                        return Response({
                            "status": "error",
                            "message": "No se encontró JSON válido en el cuerpo"
                        }, status=400)

                    # 4. Limpiar posibles caracteres extraños al final
                    json_text = json_part.split('--myboundary')[0].strip()

                    # 5. Validar balance de llaves
                    open_braces = json_text.count('{')
                    close_braces = json_text.count('}')

                    if open_braces != close_braces:
                        return Response({
                            "status": "error",
                            "message": "El JSON está desbalanceado",
                            "detail": f"Se encontraron {open_braces} {{ y {close_braces} }}"
                        }, status=400)

                    # 6. Parsear el JSON
                    try:
                        data = json.loads(json_text)
                    except json.JSONDecodeError as e:
                        return Response({
                            "status": "error",
                            "message": "El JSON está malformado",
                            "error": str(e)
                        }, status=400)

                except Exception as e:
                    return Response({
                        "status": "error",
                        "message": "Error interno al procesar la solicitud",
                        "error": str(e)
                    }, status=500)

            elif "application/json" in content_type:
                try:
                    data = json.loads(raw_body)
                except json.JSONDecodeError as e:
                    return Response({
                        "status": "error",
                        "message": "JSON malformado",
                        "error": str(e)
                    }, status=400)
            else:
                return Response({
                    "status": "error",
                    "message": f"Content-Type no soportado: {content_type}. Use 'multipart/x-mixed-replace' o 'application/json'"
                }, status=415)

            # Si data sigue siendo None (no debería ocurrir si los pasos anteriores son correctos)
            if data is None:
                return Response({
                    "status": "error",
                    "message": "Error interno: no se pudo parsear el cuerpo de la solicitud"
                }, status=500)

            # Resto de tu lógica...
            if data.get("Events") and isinstance(data["Events"], list):
                event = data["Events"][0]
                data = event.get("Data", {})

            if "UserID" in data and "CreateTime" in data:
                user_id_raw = data.get("UserID")
                create_time_str = data.get("CreateTime")
                user_name = data.get("CardName")

                if not user_id_raw or not create_time_str:
                    raise InvalidFacialRecognitionData("Faltan 'UserID' o 'CreateTime' en los datos")

                user_id = str(user_id_raw)

                try:
                    timestamp = int(create_time_str)
                    utc_dt = datetime.utcfromtimestamp(timestamp).replace(tzinfo=pytz.UTC)
                    zona_local = pytz.timezone('America/Caracas')
                    local_dt = utc_dt.astimezone(zona_local)
                except ValueError as e:
                    return Response({
                        "status": "error",
                        "message": "'CreateTime' debe ser un timestamp Unix válido",
                        "error": str(e)
                    }, status=400)

                try:
                    tenant = get_tenant_model().objects.get(schema_name=schema_name)
                    with tenant_context(tenant):
                        clean_data = json.loads(json.dumps(data))

                        evento = FacialRecognitionEvent(
                            user_id=user_id,
                            user_name=user_name,
                            event_time=utc_dt,
                            raw_data=clean_data,
                            location=location,
                            movement_type=movement_type
                        )
                        evento.full_clean()
                        evento.save()
                except ValidationError as ve:
                    return Response({
                        "status": "error",
                        "message": "Error de validación en modelo",
                        "error": ve.message_dict
                    }, status=400)
                except Exception as e:
                    return Response({
                        "status": "error",
                        "message": "Error guardando el evento",
                        "error": str(e)
                    }, status=500)

                return Response({
                    "status": "success",
                    "message": "Evento de reconocimiento facial registrado",
                    "user_id": user_id,
                    "local_time": local_dt.strftime("%Y-%m-%d %H:%M:%S"),
                    "utc_time": utc_dt.strftime("%Y-%m-%d %H:%M:%S")
                }, status=200)

        except InvalidFacialRecognitionData as e:
            return Response({
                "status": "error",
                "message": str(e)
            }, status=400)

        except Exception as e:
            return Response({
                "status": "error",
                "message": "Error interno del servidor",
                "error": str(e)
            }, status=500)