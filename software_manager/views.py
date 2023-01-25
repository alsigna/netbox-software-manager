from copy import deepcopy
from datetime import datetime

import pytz
from dcim.models import Device, DeviceType
from django.conf import settings
from django.contrib import messages
from django.core.handlers.wsgi import WSGIRequest
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views import View
from django_rq import get_queue
from netbox.views.generic import BulkDeleteView, ObjectDeleteView, ObjectEditView, ObjectListView, ObjectView

from .choices import TaskStatusChoices
from .filtersets import GoldenImageFilterSet, ScheduledTaskFilterSet, SoftwareImageFilterSet
from .forms import (
    GoldenImageAddForm,
    GoldenImageFilterForm,
    ScheduledTaskCreateForm,
    ScheduledTaskFilterForm,
    SoftwareImageEditForm,
    SoftwareImageFilterForm,
)
from .models import GoldenImage, ScheduledTask, SoftwareImage
from .tables import (
    GoldenImageListTable,
    ScheduledTaskBulkDeleteTable,
    ScheduledTaskTable,
    ScheduleTasksTable,
    SoftwareImageListTable,
    UpgradeDeviceListTable,
)

PLUGIN_SETTINGS = settings.PLUGINS_CONFIG.get("software_manager", dict())
CF_NAME_SW_VERSION = PLUGIN_SETTINGS.get("CF_NAME_SW_VERSION", "")
UPGRADE_QUEUE = PLUGIN_SETTINGS.get("UPGRADE_QUEUE", "")

########################################################################
#                          SoftwareImage
########################################################################


class SoftwareImageView(ObjectView):
    queryset = SoftwareImage.objects.all()


class SoftwareImageList(ObjectListView):
    queryset = SoftwareImage.objects.all()
    table = SoftwareImageListTable
    filterset = SoftwareImageFilterSet
    filterset_form = SoftwareImageFilterForm
    actions = ("add", "bulk_delete")


class SoftwareImageAdd(ObjectEditView):
    queryset = SoftwareImage.objects.all()
    form = SoftwareImageEditForm

    def get_return_url(self, *args, **kwargs) -> str:
        return reverse("plugins:software_manager:softwareimage_list")


class SoftwareImageEdit(ObjectEditView):
    queryset = SoftwareImage.objects.all()
    form = SoftwareImageEditForm


class SoftwareImageDelete(ObjectDeleteView):
    queryset = SoftwareImage.objects.all()

    def get_return_url(self, *args, **kwargs) -> str:
        return reverse("plugins:software_manager:softwareimage_list")


class SoftwareImageBulkDelete(BulkDeleteView):
    queryset = SoftwareImage.objects.all()
    table = SoftwareImageListTable


########################################################################
#                          GoldenImage
########################################################################


class GoldenImageList(ObjectListView):
    queryset = DeviceType.objects.all()
    table = GoldenImageListTable
    filterset = GoldenImageFilterSet
    filterset_form = GoldenImageFilterForm
    actions = ()


class GoldenImageAdd(ObjectEditView):
    queryset = GoldenImage.objects.all()
    form = GoldenImageAddForm
    default_return_url = "plugins:software_manager:goldenimage_list"

    def get(self, request, pid_pk: int, *args, **kwargs):
        instance = GoldenImage(pid=DeviceType.objects.get(pk=pid_pk))
        form = GoldenImageAddForm(instance=instance)
        return render(
            request,
            "generic/object_edit.html",
            {
                "object": instance,
                "form": form,
                "return_url": reverse("plugins:software_manager:goldenimage_list"),
            },
        )

    def post(self, request, *args, **kwargs):
        pid = request.POST.get("device_pid", None)
        if not pid:
            messages.error(request, "No PID")
            return redirect(reverse("plugins:software_manager:goldenimage_list"))

        sw = request.POST.get("sw", None)
        if not sw:
            messages.error(request, "No SW")
            return redirect(reverse("plugins:software_manager:goldenimage_list"))

        if not DeviceType.objects.filter(model__iexact=pid).exists():
            messages.error(request, "Incorrect PID")
            return redirect(reverse("plugins:software_manager:goldenimage_list"))

        if not SoftwareImage.objects.filter(pk=sw).exists():
            messages.error(request, "Incorrect SW")
            return redirect(reverse("plugins:software_manager:goldenimage_list"))

        gi = GoldenImage.objects.create(
            pid=DeviceType.objects.get(model__iexact=pid), sw=SoftwareImage.objects.get(pk=sw)
        )
        gi.save()

        messages.success(request, f"Assigned Golden Image for {pid}: {gi.sw}")
        return redirect(reverse("plugins:software_manager:goldenimage_list"))


class GoldenImageEdit(ObjectEditView):
    queryset = GoldenImage.objects.all()
    form = GoldenImageAddForm
    default_return_url = "plugins:software_manager:goldenimage_list"


class GoldenImageDelete(ObjectDeleteView):
    queryset = GoldenImage.objects.all()
    default_return_url = "plugins:software_manager:goldenimage_list"


########################################################################
#                          UpgradeDevice
########################################################################


class UpgradeDeviceList(ObjectListView):
    queryset = (
        Device.objects.all()
        .prefetch_related(
            "primary_ip4",
            "tenant",
            "device_type",
            "device_type__golden_image",
        )
        .order_by("name")
    )
    actions = ()
    table = UpgradeDeviceListTable
    template_name = "software_manager/upgradedevice_list.html"


def submit_tasks(request: WSGIRequest) -> HttpResponseRedirect:
    filled_form = ScheduledTaskCreateForm(request.POST)
    if not filled_form.is_valid():
        messages.error(request, "Error form is not valid")
        return redirect(
            to=reverse("plugins:software_manager:upgradedevice_list"),
            permanent=False,
        )

    checked_fields = request.POST.getlist("_nullify")
    data = deepcopy(filled_form.cleaned_data)

    if "scheduled_time" not in checked_fields and not data["scheduled_time"]:
        messages.error(request, "Job start-time was not set")
        return redirect(
            to=reverse("plugins:software_manager:upgradedevice_list"),
            permanent=False,
        )

    if "scheduled_time" in checked_fields:
        start_now = datetime.now().replace(microsecond=0).astimezone(pytz.timezone(settings.TIME_ZONE))
    else:
        start_now = None

    for device in data["pk"]:
        if start_now is not None:
            data["scheduled_time"] = start_now

        task = ScheduledTask(
            device=device,
            task_type=data["task_type"],
            scheduled_time=data["scheduled_time"],
            mw_duration=int(data["mw_duration"]),
            status=TaskStatusChoices.STATUS_SCHEDULED,
            user=request.user.username,  # type: ignore
            transfer_method=data["transfer_method"],
        )
        task.save()

        queue = get_queue(UPGRADE_QUEUE)
        queue_args = {
            "f": "software_manager.worker.upgrade_device",
            "job_timeout": 3600,
            "args": [task.pk],
        }
        if start_now is not None:
            job = queue.enqueue(**queue_args)
        else:
            job = queue.enqueue_at(
                datetime=data["scheduled_time"],
                **queue_args,
            )

        task.job_id = job.id
        task.save()

    return redirect(
        to=reverse("plugins:software_manager:scheduledtask_list"),
        permanent=False,
    )


class UpgradeDeviceScheduler(View):
    def post(self, request: WSGIRequest) -> HttpResponse | HttpResponseRedirect:
        if "_create" in request.POST:
            return submit_tasks(request=request)
        else:
            if "_devices" in request.POST:
                device_list = [int(pk) for pk in request.POST.getlist("pk")]
            elif "_tasks" in request.POST:
                device_list = [int(ScheduledTask.objects.get(pk=pk).device.pk) for pk in request.POST.getlist("pk")]
            else:
                device_list = []

            selected_devices = Device.objects.filter(pk__in=device_list)

            if not selected_devices:
                if "_tasks" in request.POST:
                    messages.warning(request, "No Scheduled Tasks were selected for re-scheduling.")
                    return redirect(reverse("plugins:software_manager:scheduledtask_list"))
                else:
                    messages.warning(request, "No devices were selected.")
                    return redirect(reverse("plugins:software_manager:upgradedevice_list"))

            return render(
                request=request,
                template_name="software_manager/scheduledtask_add.html",
                context={
                    "form": ScheduledTaskCreateForm(initial={"pk": device_list}),
                    "table": ScheduleTasksTable(selected_devices),
                    "return_url": reverse("plugins:software_manager:upgradedevice_list"),
                    "next_url": reverse("plugins:software_manager:scheduledtask_list"),
                },
            )


########################################################################
#                          ScheduledTask
########################################################################


class ScheduledTaskList(ObjectListView):
    queryset = ScheduledTask.objects.all()
    table = ScheduledTaskTable
    filterset = ScheduledTaskFilterSet
    filterset_form = ScheduledTaskFilterForm
    actions = ()
    template_name = "software_manager/scheduledtask_list.html"

    def post(self, request, *args, **kwargs):
        if "_confirm" in request.POST:
            pk = request.POST.get("_confirm", None)
            if pk is not None:
                task = ScheduledTask.objects.get(pk=int(pk))
                task.confirmed = not task.confirmed
                task.save()
                messages.success(request, f'ACK changed to "{task.confirmed}" for job id "{task.job_id}"')
            else:
                messages.warning(request, "Missed pk, unknow Error")
        return redirect(request.get_full_path())


class ScheduledTaskInfo(ObjectView):
    queryset = ScheduledTask.objects.all()


class ScheduledTaskDelete(ObjectDeleteView):
    queryset = ScheduledTask.objects.all()
    default_return_url = "plugins:software_manager:scheduledtask_list"


class ScheduledTaskBulkDelete(BulkDeleteView):
    queryset = ScheduledTask.objects.all()
    table = ScheduledTaskBulkDeleteTable
    default_return_url = "plugins:software_manager:scheduledtask_list"
