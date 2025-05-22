from rest_framework.views import APIView
from django_tenants.utils import tenant_context
from django.http import JsonResponse


class SecureAPIView(APIView):
    def dispatch(self, request, *args, **kwargs):
        if not hasattr(request, 'tenant') and not request.api_consumer.has_full_access:
            return JsonResponse({'error': 'Tenant not specified'}, status=400)

        if hasattr(request, 'tenant'):
            if not request.api_consumer.can_access_tenant(request.tenant):
                return JsonResponse({'error': 'Access denied for this tenant'}, status=403)

        with tenant_context(request.tenant if hasattr(request, 'tenant') else None):
            return super().dispatch(request, *args, **kwargs)