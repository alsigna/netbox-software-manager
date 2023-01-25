from dcim.models import DeviceType
from django.db.models import Q
from django_filters import DateTimeFromToRangeFilter
from netbox.filtersets import NetBoxModelFilterSet

from .models import ScheduledTask, SoftwareImage


class SoftwareImageFilterSet(NetBoxModelFilterSet):
    class Meta:
        model = SoftwareImage
        fields = (
            "filename",
            "md5sum",
            "version",
            "comments",
        )

    def search(self, queryset, name, value):
        if not value.strip():
            return queryset
        qs_filter = (
            Q(filename__icontains=value)
            | Q(md5sum__icontains=value)
            | Q(version__icontains=value)
            | Q(comments__icontains=value)
        )
        return queryset.filter(qs_filter)


class GoldenImageFilterSet(NetBoxModelFilterSet):
    class Meta:
        model = DeviceType
        fields = (
            "id",
            "part_number",
            "model",
            "manufacturer_id",
            "golden_image",
        )

    def search(self, queryset, name, value):
        if not value.strip():
            return queryset
        qs_filter = (
            Q(id__in=value)
            | Q(part_number__icontains=value)
            | Q(manufacturer_id__in=value)
            | Q(model__icontains=value)
            | Q(golden_image__sw__version__icontains=value)
            | Q(golden_image__sw__filename__icontains=value)
        )
        return queryset.filter(qs_filter)


class ScheduledTaskFilterSet(NetBoxModelFilterSet):
    scheduled_time = DateTimeFromToRangeFilter()
    start_time = DateTimeFromToRangeFilter()
    end_time = DateTimeFromToRangeFilter()

    class Meta:
        model = ScheduledTask
        fields = (
            "status",
            "task_type",
            "confirmed",
            "job_id",
            "scheduled_time",
            "start_time",
            "end_time",
        )

    def search(self, queryset, name, value):
        if not value.strip():
            return queryset
        qs_filter = (
            Q(device__name__icontains=value)
            | Q(task_type__icontains=value)
            | Q(status__icontains=value)
            | Q(job_id__icontains=value)
        )
        return queryset.filter(qs_filter)
