from django.urls import path
from . import views

urlpatterns = [
    path('software/',                views.SoftwareList.as_view(),   name='software_list'),
    path('software/add',             views.SoftwareAdd.as_view(),    name='software_add'),
    path('software/<int:pk>/edit',   views.SoftwareAdd.as_view(),    name='software_edit'),
    path('software/<int:pk>/delete', views.SoftwareDelele.as_view(), name='software_delete'),

    path('golden_image/',                 views.GoldenImageList.as_view(),   name='golden_image_list'),
    path('golden_image/<int:pid_pk>/add', views.GoldenImageAdd.as_view(),    name='golden_image_add'),
    path('golden_image/<int:pk>/edit',    views.GoldenImageEdit.as_view(),   name='golden_image_edit'),
    path('golden_image/<int:pk>/delete',  views.GoldenImageDelete.as_view(), name='golden_image_delete'),

    path('upgrade_device/',          views.UpgradeDeviceList.as_view(),      name='upgrade_device_list'),
    path('upgrade_device/scheduler', views.UpgradeDeviceScheduler.as_view(), name='upgrade_device_scheduler'),

    path('scheduled_task/',                views.ScheduledTaskList.as_view(),       name='scheduled_task_list'),
    path('scheduled_task/delete',          views.ScheduledTaskBulkDelete.as_view(), name='scheduled_task_bulk_delete'),
    path('scheduled_task/<int:pk>/delete', views.ScheduledTaskDelete.as_view(),     name='scheduled_task_delete'),
    path('scheduled_task/<int:pk>/',       views.ScheduledTaskInfo.as_view(),       name='scheduled_task_info'),
]
