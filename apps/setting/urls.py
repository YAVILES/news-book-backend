from rest_framework import routers
from .views import NotificationViewSet, IbartiViewSet, TaskResultViewSet, PeriodicTaskViewSet

router = routers.SimpleRouter()
router.register(r'notification', NotificationViewSet)
router.register(r'ibarti', IbartiViewSet, basename='ibarti')
router.register(r'task_results', TaskResultViewSet)
router.register(r'periodic_task', PeriodicTaskViewSet)

urlpatterns = [
]

urlpatterns += router.urls
