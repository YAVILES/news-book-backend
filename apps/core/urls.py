from rest_framework import routers
from .views import TypeNewsViewSet

router = routers.SimpleRouter()
router.register(r'type_news', TypeNewsViewSet)

urlpatterns = [
]

urlpatterns += router.urls
