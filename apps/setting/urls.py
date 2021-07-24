from rest_framework import routers
from .views import NotificationViewSet

router = routers.SimpleRouter()
router.register(r'notification', NotificationViewSet)

urlpatterns = [
]

urlpatterns += router.urls
