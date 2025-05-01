from django.http import JsonResponse
from django_tenants.utils import get_tenant_model
from apps.api.models import APIConsumer


class APIAuthMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Solo aplica a rutas de API
        if not request.path.startswith('/api/api/'):
            return self.get_response(request)

        # Obtiene token de headers O parámetros
        api_token = self._get_token_from_request(request)
        if not api_token:
            return JsonResponse({'error': 'API token required'}, status=401)

        # Obtiene schema de headers O parámetros
        schema_name = self._get_schema_from_request(request)

        try:
            consumer = APIConsumer.objects.get(token=api_token, is_active=True)
            request.api_consumer = consumer

            # Lógica de tenant
            if schema_name:
                tenant = get_tenant_model().objects.get(schema_name=schema_name)
                if not consumer.can_access_tenant(tenant):
                    return JsonResponse({'error': 'Token not authorized for this tenant'}, status=403)
                request.tenant = tenant
            elif not consumer.has_full_access:
                return JsonResponse({'error': 'Schema required for this token'}, status=400)

            consumer.last_used_at = timezone.now()
            consumer.usage_count += 1
            consumer.save()

        except APIConsumer.DoesNotExist:
            return JsonResponse({'error': 'Invalid API token'}, status=401)
        except get_tenant_model().DoesNotExist:
            return JsonResponse({'error': 'Invalid tenant schema'}, status=400)

        return self.get_response(request)

    def _get_token_from_request(self, request):
        """Obtiene token de headers o query params"""
        return (
                request.headers.get('X-API-Token')
                or request.GET.get('api_token')
                or request.POST.get('api_token')
        )

    def _get_schema_from_request(self, request):
        """Obtiene schema de headers o query params"""
        return (
                request.headers.get('X-Dts-Schema')
                or request.GET.get('schema')
                or request.POST.get('schema')
        )