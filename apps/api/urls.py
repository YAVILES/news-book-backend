from django.urls import path
from rest_framework import permissions
from drf_yasg2.utils import swagger_auto_schema
from apps.api.views import NoveltiesAPI

urlpatterns = [
    path('novelties/', NoveltiesAPI.as_view(), name='zoho-novelties')
]