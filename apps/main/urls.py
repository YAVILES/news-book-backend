from rest_framework import routers
from .views import TypePersonViewSet, PersonViewSet, VehicleViewSet, MaterialViewSet, NewsViewSet, ScheduleViewSet, \
    LocationViewSet, PointViewSet, EquipmentToolsViewSet, NewsLinkViewSet

router = routers.SimpleRouter()
router.register(r'type_person', TypePersonViewSet)
router.register(r'person', PersonViewSet)
router.register(r'vehicle', VehicleViewSet)
router.register(r'material', MaterialViewSet)
router.register(r'schedule', ScheduleViewSet)
router.register(r'news', NewsViewSet)
router.register(r'location', LocationViewSet)
router.register(r'point', PointViewSet)
router.register(r'equipment_tool', EquipmentToolsViewSet)
router.register(r'newslink', NewsLinkViewSet)
urlpatterns = [
]

urlpatterns += router.urls
