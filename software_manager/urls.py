from django.urls import path
from netbox.views.generic import ObjectChangeLogView

from .models import SoftwareImage
from .views import (
    GoldenImageAdd,
    GoldenImageDelete,
    GoldenImageEdit,
    GoldenImageList,
    ScheduledTaskBulkDelete,
    ScheduledTaskDelete,
    ScheduledTaskInfo,
    ScheduledTaskList,
    SoftwareImageAdd,
    SoftwareImageBulkDelete,
    SoftwareImageDelete,
    SoftwareImageEdit,
    SoftwareImageList,
    SoftwareImageView,
    UpgradeDeviceList,
    UpgradeDeviceScheduler,
)

app_name = "software_manager"

urlpatterns = [
    # software image
    path("software-image/", SoftwareImageList.as_view(), name="softwareimage_list"),
    path("software-image/add", SoftwareImageAdd.as_view(), name="softwareimage_add"),
    path("software-image/delete", SoftwareImageBulkDelete.as_view(), name="softwareimage_bulk_delete"),
    path("software-image/<int:pk>/", SoftwareImageView.as_view(), name="softwareimage"),
    path("software-image/<int:pk>/edit", SoftwareImageEdit.as_view(), name="softwareimage_edit"),
    path("software-image/<int:pk>/delete", SoftwareImageDelete.as_view(), name="softwareimage_delete"),
    path(
        "software-image/<int:pk>/changelog/",
        ObjectChangeLogView.as_view(),
        name="softwareimage_changelog",
        kwargs={"model": SoftwareImage},
    ),
    # golden image
    path("golden-image/", GoldenImageList.as_view(), name="goldenimage_list"),
    path("golden-image/<int:pid_pk>/add", GoldenImageAdd.as_view(), name="goldenimage_add"),
    path("golden-image/<int:pk>/edit", GoldenImageEdit.as_view(), name="goldenimage_edit"),
    path("golden-image/<int:pk>/delete", GoldenImageDelete.as_view(), name="goldenimage_delete"),
    # upgrade device
    path("upgrade-device/", UpgradeDeviceList.as_view(), name="upgradedevice_list"),
    path("upgrade-device/scheduler", UpgradeDeviceScheduler.as_view(), name="upgradedevice_scheduler"),
    # scheduled tsaks
    path("scheduled-task/", ScheduledTaskList.as_view(), name="scheduledtask_list"),
    path("scheduled-task/<int:pk>/", ScheduledTaskInfo.as_view(), name="scheduledtask"),
    path("scheduled-task/<int:pk>/delete", ScheduledTaskDelete.as_view(), name="scheduledtask_delete"),
    path("scheduled-task/delete", ScheduledTaskBulkDelete.as_view(), name="scheduledtask_bulk_delete"),
]
