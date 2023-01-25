from netbox.api.routers import NetBoxRouter

from .views import GoldenImageViewSet, ScheduledTaskViewSet, SoftwareImageViewSet

app_name = "software_manager"

router = NetBoxRouter()

router.register(r"software-image", SoftwareImageViewSet)
router.register(r"golden-image", GoldenImageViewSet)
router.register(r"scheduled-task", ScheduledTaskViewSet)

urlpatterns = router.urls
