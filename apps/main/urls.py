from rest_framework import routers
from .views import AccessGroupViewSet, TypePersonViewSet, PersonViewSet, VehicleViewSet, MaterialViewSet, NewsViewSet, ScheduleViewSet, \
    LocationViewSet, PointViewSet, EquipmentToolsViewSet, NewsLinkViewSet, AccessEntryViewSet

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
router.register(r'access-groups', AccessGroupViewSet, basename='access-group')
router.register(r'access-entries', AccessEntryViewSet, basename='access-entries')

urlpatterns = [
]

urlpatterns += router.urls
