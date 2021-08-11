from rest_framework import routers
from .views import TypePersonViewSet, PersonViewSet, VehicleViewSet, MaterialViewSet, NewsViewSet, ScheduleViewSet

router = routers.SimpleRouter()
router.register(r'type_person', TypePersonViewSet)
router.register(r'person', PersonViewSet)
router.register(r'vehicle', VehicleViewSet)
router.register(r'material', MaterialViewSet)
router.register(r'schedule', ScheduleViewSet)
router.register(r'news', NewsViewSet)

urlpatterns = [
]

urlpatterns += router.urls
