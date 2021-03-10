import django_filters

from django.db.models import Q

from dcim.models import Device, DeviceRole, DeviceType
from tenancy.filters import TenancyFilterSet
from extras.filters import CustomFieldModelFilterSet
from utilities.filters import BaseFilterSet, TagFilter

from .models import ScheduledTask, SoftwareImage
from .choices import TaskTypeChoices, TaskStatusChoices


class ScheduledTaskFilter(BaseFilterSet):
    q = django_filters.CharFilter(
        method='search',
        label='Search',
    )
    task_type = django_filters.MultipleChoiceFilter(
        choices=TaskTypeChoices,
        null_value=None
    )
    status = django_filters.MultipleChoiceFilter(
        choices=TaskStatusChoices,
        null_value=None
    )
    confirmed = django_filters.BooleanFilter(
        label='Is confirmed',
    )

    scheduled_time = django_filters.DateTimeFromToRangeFilter()
    start_time = django_filters.DateTimeFromToRangeFilter()
    end_time = django_filters.DateTimeFromToRangeFilter()

    class Meta:
        model = ScheduledTask
        fields = ['task_type', 'status', 'scheduled_time', 'start_time', 'end_time']

    def search(self, queryset, name, value):
        if not value.strip():
            return queryset
        qs_filter = (
            Q(device__name__icontains=value)
            | Q(task_type__icontains=value)
            | Q(status__icontains=value)
        )
        return queryset.filter(qs_filter)


class UpgradeDeviceFilter(
    BaseFilterSet,
    TenancyFilterSet,
    CustomFieldModelFilterSet,
):
    q = django_filters.CharFilter(
        method='search',
        label='Search',
    )
    device_type_id = django_filters.ModelMultipleChoiceFilter(
        queryset=DeviceType.objects.all(),
        label='Device type (ID)',
    )
    role_id = django_filters.ModelMultipleChoiceFilter(
        field_name='device_role_id',
        queryset=DeviceRole.objects.all(),
        label='Role (ID)',
    )
    role = django_filters.ModelMultipleChoiceFilter(
        field_name='device_role__slug',
        queryset=DeviceRole.objects.all(),
        to_field_name='slug',
        label='Role (slug)',
    )
    model = django_filters.ModelMultipleChoiceFilter(
        field_name='device_type__slug',
        queryset=DeviceType.objects.all(),
        to_field_name='slug',
        label='Device model (slug)',
    )
    target_sw = django_filters.ModelMultipleChoiceFilter(
        field_name='device_type__golden_image__sw__version',
        queryset=SoftwareImage.objects.all(),
        to_field_name='version',
        label='Target Version',
    )

    tag = TagFilter()

    class Meta:
        model = Device
        fields = ['id', 'name', 'model', 'target_sw']

    def search(self, queryset, name, value):
        if not value.strip():
            return queryset
        return queryset.filter(
            Q(name__icontains=value)
            | Q(tenant__name__icontains=value)
            | Q(primary_ip4__address__icontains=value)
            | Q(custom_field_data__icontains=value)
            | Q(device_role__name__icontains=value)
            | Q(device_type__model__icontains=value)
            | Q(device_type__golden_image__sw__version__icontains=value)
        ).distinct()
