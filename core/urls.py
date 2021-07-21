from rest_framework import routers
from .views import TypePersonViewSet, PersonViewSet, ClassificationNewsViewSet, TypeNewsViewSet, VehicleViewSet, \
    MaterialViewSet, NewsViewSet

router = routers.SimpleRouter()
router.register(r'type_person', TypePersonViewSet)
router.register(r'person', PersonViewSet)
router.register(r'classification_news', ClassificationNewsViewSet)
router.register(r'type_news', TypeNewsViewSet)
router.register(r'vehicle', VehicleViewSet)
router.register(r'material', MaterialViewSet)
router.register(r'news', NewsViewSet)

urlpatterns = [
]

urlpatterns += router.urls
