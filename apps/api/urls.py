from django.urls import path
from rest_framework import permissions
from drf_yasg2.utils import swagger_auto_schema
from apps.api.views import NoveltiesAPI, TypeNewsAPI, ClientsAPI, NoveltyByTypeAPI

urlpatterns = [
    path('novelties/', NoveltiesAPI.as_view(), name='zoho-novelties'),
    path('novelties/<str:type_new>/', NoveltyByTypeAPI.as_view(), name='novelty-by-type'),
    path('types/', TypeNewsAPI.as_view(), name='zoho-types'),
    path('clients/', ClientsAPI.as_view(), name='zoho-clients'),
]