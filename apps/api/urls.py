from django.urls import path
from rest_framework import permissions
from drf_yasg2.utils import swagger_auto_schema
from apps.api.views import FacialRecognitionAPI, NoveltiesAPI, TypeNewsAPI, ClientsAPI, NoveltyByTypeAPI, TypePersonAPI

urlpatterns = [
    path('novelties/', NoveltiesAPI.as_view(), name='zoho-novelties'),
    path('novelties/<str:type_new>/', NoveltyByTypeAPI.as_view(), name='novelty-by-type'),
    path('types/', TypeNewsAPI.as_view(), name='zoho-types'),
    path('clients/', ClientsAPI.as_view(), name='zoho-clients'),
    path('type_persons/', TypePersonAPI.as_view(), name='type-persons'),
    # path('facial-recognition/', FacialRecognitionAPI.as_view(), name='facial-recognition'),
    path('facial-recognition/<str:schema_name>/', FacialRecognitionAPI.as_view(), name='facial-recognition-with-params')
]