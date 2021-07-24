from rest_framework import routers
from .views import ClientViewSet, DomainViewSet

router = routers.SimpleRouter()
router.register(r'client', ClientViewSet)
router.register(r'domain', DomainViewSet)
urlpatterns = [
]

urlpatterns += router.urls
