import xlsxwriter
import io
import os
import pytz

from copy import deepcopy
from datetime import datetime
from django_rq import get_scheduler, get_queue
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.views.generic import View
from django.urls import reverse
from django.http import HttpResponse
from django.conf import settings

from netbox.views.generic import ObjectListView, ObjectEditView, ObjectDeleteView, BulkDeleteView
from dcim.models import DeviceType, Device

from .models import SoftwareImage, GoldenImage, ScheduledTask
from .tables import SoftwareListTable, GoldenImageListTable, UpgradeDeviceListTable, ScheduledTaskTable
from .filters import UpgradeDeviceFilter, ScheduledTaskFilter
from .forms import (
    UpgradeDeviceFilterForm,
    ScheduledTaskCreateForm,
    ScheduledTaskFilterForm,
    SoftwareImageAddForm,
    GoldenImageAddForm,
)
from .choices import TaskStatusChoices


TIME_ZONE = os.environ.get("TIME_ZONE", "UTC")
PLUGIN_SETTINGS = settings.PLUGINS_CONFIG.get("software_manager", dict())
CF_NAME_SW_VERSION = PLUGIN_SETTINGS.get("CF_NAME_SW_VERSION", "")
UPGRADE_QUEUE = PLUGIN_SETTINGS.get("UPGRADE_QUEUE", "")


class SoftwareList(ObjectListView):
    queryset = SoftwareImage.objects.all()
    table = SoftwareListTable
    template_name = "software_manager/software_list.html"


class SoftwareAdd(ObjectEditView):
    queryset = SoftwareImage.objects.all()
    model_form = SoftwareImageAddForm
    default_return_url = "plugins:software_manager:software_list"


class SoftwareDelele(ObjectDeleteView):
    queryset = SoftwareImage.objects.all()
    default_return_url = "plugins:software_manager:software_list"


class GoldenImageList(ObjectListView):
    queryset = DeviceType.objects.all()
    table = GoldenImageListTable
    template_name = "software_manager/golden_image_list.html"

    def export_to_excel(self):
        data = []
        output = io.BytesIO()
        header = [
            {"header": "Hostname"},
            {"header": "PID"},
            {"header": "IP Address"},
            {"header": "Hub"},
            {"header": "SW"},
            {"header": "Golden Image"},
        ]
        width = [len(i["header"]) + 2 for i in header]
        devices = (
            Device.objects.all()
            .prefetch_related(
                "primary_ip4",
                "tenant",
                "device_type",
                "device_type__golden_image",
            )
            .order_by("name")
        )
        for d in devices:
            if d.name:
                hostname = d.name
            else:
                hostname = "unnamed device"
            k = [
                hostname,
                d.device_type.model,
                str(d.primary_ip4).split("/")[0],
                str(d.tenant),
                d.custom_field_data[CF_NAME_SW_VERSION],
            ]
            if hasattr(d.device_type, "golden_image"):
                k.append(
                    str(
                        str(d.custom_field_data[CF_NAME_SW_VERSION]).upper()
                        == str(d.device_type.golden_image.sw.version).upper()
                    )
                )
            else:
                k.append("False")
            data.append(k)
            w = [len(i) for i in k]
            width = [max(width[i], w[i]) for i in range(0, len(width))]
        workbook = xlsxwriter.Workbook(
            output,
            {"remove_timezone": True, "default_date_format": "yyyy-mm-dd"},
        )
        worksheet = workbook.add_worksheet("SIAR")
        worksheet.add_table(0, 0, Device.objects.all().count(), len(header) - 1, {"columns": header, "data": data})
        for i in range(0, len(width)):
            worksheet.set_column(i, i, width[i])
        workbook.close()
        output.seek(0)
        return output

    def get(self, request, *args, **kwargs):
        if "to_excel" in request.GET.keys():
            filename = f'siar_{datetime.now().astimezone(pytz.timezone(TIME_ZONE)).strftime("%Y%m%d_%H%M%S")}.xlsx'
            response = HttpResponse(
                self.export_to_excel(),
                content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
            response["Content-Disposition"] = f'attachment; filename="{filename}"'
            return response
        return super().get(request, *args, **kwargs)


class GoldenImageAdd(ObjectEditView):
    queryset = GoldenImage.objects.all()
    model_form = GoldenImageAddForm
    default_return_url = "plugins:software_manager:golden_image_list"

    def get(self, request, pk=None, pid_pk=None, *args, **kwargs):
        if pk is not None:
            pass
        else:
            i = GoldenImage(pid=DeviceType.objects.get(pk=pid_pk))
            i.pk = True
        form = GoldenImageAddForm(instance=i)
        return render(
            request,
            "generic/object_edit.html",
            {
                "obj": i,
                "obj_type": i._meta.verbose_name,
                "form": form,
                "return_url": reverse("plugins:software_manager:golden_image_list"),
            },
        )

    def post(self, request, pk=None, pid_pk=None, *args, **kwargs):
        pid = request.POST.get("device_pid", None)
        if not pid:
            messages.error(request, "No PID")
            return redirect(reverse("plugins:software_manager:golden_image_list"))

        sw = request.POST.get("sw", None)
        if not sw:
            messages.error(request, "No SW")
            return redirect(reverse("plugins:software_manager:golden_image_list"))

        if not DeviceType.objects.filter(model__iexact=pid).count():
            messages.error(request, "Incorrect PID")
            return redirect(reverse("plugins:software_manager:golden_image_list"))

        if not SoftwareImage.objects.filter(pk=sw).count():
            messages.error(request, "Incorrect SW")
            return redirect(reverse("plugins:software_manager:golden_image_list"))

        gi = GoldenImage.objects.create(
            pid=DeviceType.objects.get(model__iexact=pid), sw=SoftwareImage.objects.get(pk=sw)
        )
        gi.save()

        messages.success(request, f"Assigned golden image {pid}: {gi.sw}")
        return redirect(reverse("plugins:software_manager:golden_image_list"))


class GoldenImageEdit(ObjectEditView):
    queryset = GoldenImage.objects.all()
    model_form = GoldenImageAddForm
    default_return_url = "plugins:software_manager:golden_image_list"


class GoldenImageDelete(ObjectDeleteView):
    queryset = GoldenImage.objects.all()
    default_return_url = "plugins:software_manager:golden_image_list"


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
    filterset = UpgradeDeviceFilter
    filterset_form = UpgradeDeviceFilterForm
    table = UpgradeDeviceListTable
    template_name = "software_manager/upgrade_device_list.html"


class UpgradeDeviceScheduler(View):
    def post(self, request):
        if "_create" in request.POST:
            s = ScheduledTaskCreateForm(request.POST)
            if s.is_valid():
                checked_fields = request.POST.getlist("_nullify")
                data = deepcopy(s.cleaned_data)
                if "scheduled_time" not in checked_fields and not data["scheduled_time"]:
                    messages.error(request, "Job start time was not set")
                    return redirect(reverse("plugins:software_manager:upgrade_device_list"))
                for i in data["pk"]:
                    if "scheduled_time" in checked_fields:
                        data["scheduled_time"] = (
                            datetime.now().replace(microsecond=0).astimezone(pytz.timezone(TIME_ZONE))
                        )
                    task = ScheduledTask(
                        device=i,
                        task_type=data["task_type"],
                        scheduled_time=data["scheduled_time"],
                        mw_duration=int(data["mw_duration"]),
                        status=TaskStatusChoices.STATUS_SCHEDULED,
                        user=request.user.username,
                        transfer_method=data["transfer_method"],
                    )
                    task.save()

                    if "scheduled_time" in checked_fields:
                        queue = get_queue(UPGRADE_QUEUE)
                        job = queue.enqueue_job(
                            queue.create_job(
                                func="software_manager.worker.upgrade_device",
                                args=[task.pk],
                                timeout=9000,
                            )
                        )
                    else:
                        scheduler = get_scheduler(UPGRADE_QUEUE)
                        job = scheduler.schedule(
                            scheduled_time=data["scheduled_time"],
                            func="software_manager.worker.upgrade_device",
                            args=[task.pk],
                            timeout=9000,
                        )
                    task.job_id = job.id
                    task.save()
                messages.success(request, f'Task {data["task_type"]} was scheduled for {len(data["pk"])} devices')
            else:
                messages.error(request, "Error form is not valid")
                return redirect(reverse("plugins:software_manager:upgrade_device_list"))
            return redirect(reverse("plugins:software_manager:scheduled_task_list"))
        else:
            if "_device" in request.POST:
                pk_list = [int(pk) for pk in request.POST.getlist("pk")]
            elif "_task" in request.POST:
                pk_list = [int(ScheduledTask.objects.get(pk=pk).device.pk) for pk in request.POST.getlist("pk")]

            selected_devices = Device.objects.filter(pk__in=pk_list)

            if not selected_devices:
                messages.warning(request, "No devices were selected.")
                return redirect(reverse("plugins:software_manager:upgrade_device_list"))

            return render(
                request,
                "software_manager/scheduledtask_add.html",
                {
                    "form": ScheduledTaskCreateForm(initial={"pk": pk_list}),
                    "parent_model_name": "Devices",
                    "model_name": "Scheduled Tasks",
                    "table": UpgradeDeviceListTable(selected_devices),
                    "return_url": reverse("plugins:software_manager:upgrade_device_list"),
                    "next_url": reverse("plugins:software_manager:scheduled_task_list"),
                },
            )


class ScheduledTaskList(ObjectListView):
    queryset = ScheduledTask.objects.all()
    table = ScheduledTaskTable
    filterset = ScheduledTaskFilter
    filterset_form = ScheduledTaskFilterForm
    template_name = "software_manager/scheduledtask_list.html"

    def post(self, request, *args, **kwargs):
        if "_confirm" in request.POST:
            pk = request.POST.get("_confirm", "")
            if pk:
                task = ScheduledTask.objects.get(pk=int(pk))
                task.confirmed = not task.confirmed
                task.save()
                messages.success(request, f'ACK changed to "{task.confirmed}" for job id "{task.job_id}"')
            else:
                messages.warning(request, "Missed pk, unknow Error")
        return redirect(request.get_full_path())


class ScheduledTaskBulkDelete(BulkDeleteView):
    queryset = ScheduledTask.objects.all()
    table = ScheduledTaskTable
    default_return_url = "plugins:software_manager:scheduled_task_list"


class ScheduledTaskDelete(ObjectDeleteView):
    queryset = ScheduledTask.objects.all()
    default_return_url = "plugins:software_manager:scheduled_task_list"


class ScheduledTaskInfo(ObjectDeleteView):
    queryset = ScheduledTask.objects.all()

    def get(self, request, pk):
        task = get_object_or_404(self.queryset, pk=pk)
        return render(
            request,
            "software_manager/scheduledtask_info.html",
            {
                "task": task,
            },
        )
