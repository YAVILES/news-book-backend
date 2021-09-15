from rest_framework import routers
from .views import NotificationViewSet, IbartiViewSet

router = routers.SimpleRouter()
router.register(r'notification', NotificationViewSet)
router.register(r'ibarti', IbartiViewSet, basename='ibarti')

urlpatterns = [
]

urlpatterns += router.urls
