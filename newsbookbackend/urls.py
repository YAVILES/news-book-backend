import debug_toolbar
from django.conf import settings
from django.conf.urls import include
from django.conf.urls import url
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include, re_path
from rest_framework import permissions
from drf_yasg2.views import get_schema_view
from drf_yasg2.utils import swagger_auto_schema
from drf_yasg2 import openapi
from rest_framework_simplejwt.views import TokenRefreshView, TokenVerifyView
from apps.api import urls as api_urls

from apps.security.views import CustomTokenObtainPairView
from apps.setting.views import TestEmailView

schema_view = get_schema_view(
    openapi.Info(
        title="Snippets API",
        default_version='v1',
        description="Test description",
        terms_of_service="https://www.google.com/policies/terms/",
        contact=openapi.Contact(email="contact@snippets.local"),
        license=openapi.License(name="BSD License"),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
    #url='http://194.163.161.64/api'
)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/customers/', include('apps.customers.urls')),
    path('api/security/', include('apps.security.urls')),
    path('api/core/', include('apps.core.urls')),
    path('api/main/', include('apps.main.urls')),
    path('api/setting/', include('apps.setting.urls')),

    path('api/accounts/', include('django.contrib.auth.urls')),

    path('api/test-email/', TestEmailView.as_view()),

    # Tokens
    path('api/token/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    # path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    # path('api/token/verify/', TokenVerifyView.as_view(), name='token_verify'),
    re_path(r'^swagger(?P<format>\.json|\.yaml)$', schema_view.without_ui(cache_timeout=0), name='schema-json'),
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
    # Short URLss
    url(r'^s/', include('django_short_url.urls', namespace='django_short_url')),

    path('api/api/', include(api_urls)),
]
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
if settings.DEBUG:
    urlpatterns += url(r'^__debug__/', include(debug_toolbar.urls)),


api_schema_view = get_schema_view(
    openapi.Info(
        title="API Libro de novedades",
        default_version='v1',
        description="Endpoints exclusivos para integraciones con terceros.",
        license=openapi.License(name="Solo uso interno"),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
    patterns=[
        path('api/api/', include(api_urls)),  # Esto conecta los endpoints con la documentación
    ],
)

urlpatterns += [
    path('api/swagger/', api_schema_view.with_ui('swagger', cache_timeout=0), name='api-swagger'),
    path('api/redoc/', api_schema_view.with_ui('redoc', cache_timeout=0), name='api-redoc'),
]

