from rest_framework import routers
from .views import UserViewSet, RoleViewSet

router = routers.SimpleRouter()
router.register(r'user', UserViewSet)
router.register(r'role', RoleViewSet)

urlpatterns = [
]

urlpatterns += router.urls
