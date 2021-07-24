from rest_framework import routers
from .views import UserViewSet, RoleViewSet, ValidUser

router = routers.SimpleRouter()
router.register(r'user', UserViewSet, basename='user')
router.register(r'group', RoleViewSet, basename='group')
router.register(r'valid', ValidUser, basename='valid')
urlpatterns = [
]

urlpatterns += router.urls
