import django_tables2 as tables
from dcim.models import Device, DeviceType
from django_tables2.utils import Accessor
from netbox.tables import NetBoxTable
from netbox.tables.columns import ActionsColumn, ColoredLabelColumn, TagColumn, ToggleColumn
from tenancy.tables import TenantColumn

from .models import ScheduledTask, SoftwareImage

SW_LIST_FILENAME = """
{% if record.image_exists %}
    <a href="{% url 'plugins:software_manager:softwareimage' pk=record.pk %}">{{ record.filename }}</a>
{% else %}
    <a href="{% url 'plugins:software_manager:softwareimage' pk=record.pk %}">{{ record }}</a>
{% endif %}
"""


SW_LIST_SIZE = """
{% if record.image_exists %}
    {{ record.image.size|filesizeformat }}
{% else %}
    <span>&mdash;</span>
{% endif %}
"""

SW_LIST_MD5SUM = """
{% if record.md5sum == record.md5sum_calculated %}
    <span class="badge bg-success" style="font-size: small; font-family: monospace">{{ record.md5sum }}</span>
{% else %}
    <span class="badge bg-danger" style="font-size: small; font-family: monospace">{{ record.md5sum|default:"&mdash;" }}</span>
{% endif %}
"""


SW_LIST_DOWNLOAD_IMAGE = """
{% if record.image_exists %}
    <a href="{{ record.image.url }}" target="_blank" class="btn btn-sm btn-primary" title="Download Image">
        <i class="mdi mdi-download"></i>
    </a>
{% else %}
    <button class="btn btn-sm btn-primary" title="Download Image" disabled="disabled">
        <i class="mdi mdi-download"></i>
    </button>
{% endif %}
"""

GOLDEN_IMAGE_FILENAME = """
{{ record.golden_image.sw.filename|default:"&mdash;" }}
"""

GOLDEN_IMAGE_ACTION = """
{% if record.golden_image %}
    <a href="{% url 'plugins:software_manager:goldenimage_edit' pk=record.golden_image.pk %}" class="btn btn-sm btn-warning" title="Edit Image">
        <i class="mdi mdi-pencil" aria-hidden="true"></i>
    </a>
    <a href="{% url 'plugins:software_manager:goldenimage_delete' pk=record.golden_image.pk %}" class="btn btn-sm btn-danger" title="Clear image">
        <i class="mdi mdi-trash-can-outline" aria-hidden="true"></i>
    </a>
{% else %}
    <a href="{% url 'plugins:software_manager:goldenimage_add' pid_pk=record.pk %}" class="btn btn-sm btn-warning" title="Add Image">
        <i class="mdi mdi-pencil" aria-hidden="true"></i>
    </a>
    <button class="btn btn-sm btn-danger" title="Clear image" disabled="disabled">
        <i class="mdi mdi-trash-can-outline" aria-hidden="true"></i>
    </button>
{% endif %}
"""

GOLDEN_IMAGE_MD5SUM = """
{% if record.golden_image.sw.md5sum == record.golden_image.sw.md5sum_calculated %}
    <span class="badge bg-success" style="font-size: small; font-family: monospace">{{ record.golden_image.sw.md5sum }}</span>
{% else %}
    <span class="badge bg-danger" style="font-size: small; font-family: monospace">{{ record.golden_image.sw.md5sum|default:"&mdash;" }}</span>
{% endif %}
"""

GOLDEN_IMAGE_PROGRESS_GRAPH = """
{% if record.golden_image %}
    {% if record.instances.count %}
        {% progress_graph record.golden_image.get_progress %}
    {% else %}
        No instances
    {% endif %}
{% else %}
    &mdash;
{% endif %}
"""

UPGRADE_TARGET_SOFTWARE = """
{{ record.device_type.golden_image.sw.version|default:"&mdash;" }}
"""

UPGRADE_CURRENT_SOFTWARE = """
{% if record|get_current_version %}
    {% if record|get_current_version == record.device_type.golden_image.sw.version %}
        <span class="badge bg-success">{{ record|get_current_version }}</span>
    {% else %}
        <span class="badge bg-warning">{{ record|get_current_version }}</span>
    {% endif %}
{% else %}
    &mdash;
{% endif %}
"""

SCHEDULED_TASK_TIME = """
{{ value|date:"SHORT_DATETIME_FORMAT" }}
"""

SCHEDULED_TASK_TYPE = """
{% if record.task_type == 'upload' %}
    <span class="badge bg-info">Upload</span>
{% elif record.task_type == 'upgrade' %}
    <span class="badge bg-primary">Upgrade</span>
{% else %}
    <span class="badge bg-secondary">Unknown</span>
{% endif %}
"""

SCHEDULED_TASK_STATUS = """
{% if record.status == 'succeeded' %}
    <span class="badge bg-success" title="Task Finished Successfully">Succeeded</span>
{% elif record.status == 'skipped' %}
    <span class="badge bg-warning" title="{{ record.message }}">Skipped</span>
{% elif record.status == 'failed' %}
    <span class="badge bg-danger" title="{{ record.message }}">Failed</span>
{% elif record.status == 'scheduled' %}
    <span class="badge bg-secondary" title="Task Scheduled">Scheduled</span>
{% elif record.status == 'running' %}
    <span class="badge bg-info" title="Task is Running">Running</span>
{% else %}
    <span class="badge bg-secondary" title="Unknown Status">Unknown</span>
{% endif %}
"""

SCHEDULED_TASK_ACTION = """
<a class="btn btn-sm btn-danger" href="{% url 'plugins:software_manager:scheduledtask_delete' pk=record.pk %}" title="Delete Task">
    <i class="mdi mdi-trash-can-outline" aria-hidden="true"></i>
</a>
"""


SCHEDULED_TASK_CONFIRMED = """
{% if record.confirmed %}
    <button type="submit" class="btn btn-sm btn-success" name="_confirm" value="{{ record.pk }}">
        <span class="mdi mdi-check-bold" aria-hidden="true"></span>
    </button>
{% else %}
    <button type="submit" class="btn btn-sm btn-danger" name="_confirm" value="{{ record.pk }}">
        <span class="mdi mdi-close-thick" aria-hidden="true"></span>
    </button>
{% endif %}
"""

SCHEDULED_TASK_JOB_ID = """
<a href="{% url 'plugins:software_manager:scheduledtask' pk=record.pk %}" style="font-size: medium; font-family: monospace">{{ record.job_id|cut_job_id }}</a>
"""


class SoftwareImageListTable(NetBoxTable):
    filename = tables.TemplateColumn(
        verbose_name="Filename",
        template_code=SW_LIST_FILENAME,
        orderable=False,
    )
    version = tables.Column(
        verbose_name="Version",
        orderable=False,
    )

    image_type = tables.Column(
        verbose_name = "Image Type",
        orderable = False,
    )

    size = tables.TemplateColumn(
        verbose_name="Size",
        template_code=SW_LIST_SIZE,
        orderable=False,
    )

    supported_devicetypes=tables.ManyToManyColumn(
        orderable=False,
        verbose_name = "Supported Device Types",
        linkify_item=True
    )

    md5sum = tables.TemplateColumn(
        verbose_name="MD5 Checksum",
        template_code=SW_LIST_MD5SUM,
        orderable=False,
    )
    tags = TagColumn(
        url_name="plugins:software_manager:softwareimage_list",
    )
    actions = ActionsColumn(
        extra_buttons=SW_LIST_DOWNLOAD_IMAGE,
    )

    class Meta(NetBoxTable.Meta):
        model = SoftwareImage
        fields = (
            "pk",
            "id",
            "filename",
            "image_type",
            "version",
            "size",
            "supported_devicetypes",
            "md5sum",
            "tags",
            "actions",
            "created",
            "last_updated",
        )
        default_columns = (
            "filename",
            "image_type",
            "version",
            "size",
            "supported_devicetypes",
            "md5sum",
            "tags",
            "actions",
        )


class GoldenImageListTable(NetBoxTable):
    model = tables.LinkColumn(
        viewname="dcim:devicetype",
        args=[Accessor("pk")],
        verbose_name="Device PID",
    )
    image = tables.TemplateColumn(
        verbose_name="Image File",
        template_code=GOLDEN_IMAGE_FILENAME,
        orderable=False,
    )
    version = tables.Column(
        verbose_name="Version",
        accessor="golden_image.sw.version",
        orderable=False,
    )
    md5sum = tables.TemplateColumn(
        verbose_name="MD5 Checksum",
        template_code=GOLDEN_IMAGE_MD5SUM,
        orderable=False,
    )
    progress = tables.TemplateColumn(
        template_code=GOLDEN_IMAGE_PROGRESS_GRAPH,
        orderable=False,
        verbose_name="Compliance",
    )

    actions = tables.TemplateColumn(
        template_code=GOLDEN_IMAGE_ACTION,
        verbose_name="",
    )

    class Meta(NetBoxTable.Meta):
        model = DeviceType
        fields = (
            "pk",
            "id",
            "model",
            "version",
            "image",
            "md5sum",
            "progress",
            "actions",
        )
        default_columns = (
            "model",
            "version",
            "image",
            "md5sum",
            "progress",
            "actions",
        )


class UpgradeDeviceListTable(NetBoxTable):
    pk = ToggleColumn(visible=True)
    name = tables.Column(linkify=True)
    t_sw = tables.TemplateColumn(
        verbose_name="Target Version",
        template_code=UPGRADE_TARGET_SOFTWARE,
        orderable=False,
    )
    c_sw = tables.TemplateColumn(
        verbose_name="Curent Version",
        template_code=UPGRADE_CURRENT_SOFTWARE,
        orderable=False,
    )
    tenant = TenantColumn()

    device_role = ColoredLabelColumn(verbose_name="Role")
    device_type = tables.LinkColumn(verbose_name="Device Type", text=lambda record: record.device_type.model)

    tags = TagColumn(url_name="plugins:software_manager:upgradedevice_list")

    actions = ActionsColumn(
        actions=(),
    )

    class Meta(NetBoxTable.Meta):
        model = Device
        fields = (
            "pk",
            "id",
            "name",
            "t_sw",
            "c_sw",
            "tenant",
            "device_role",
            "device_type",
            "tags",
        )
        default_columns = (
            "pk",
            "name",
            "t_sw",
            "c_sw",
            "tenant",
            "device_role",
            "device_type",
            "tags",
        )


class ScheduleTasksTable(UpgradeDeviceListTable):
    pk = ToggleColumn(visible=False)

    class Meta(NetBoxTable.Meta):
        model = Device
        fields = (
            "name",
            "t_sw",
            "c_sw",
            "tenant",
            "device_role",
            "device_type",
            "tags",
        )


class ScheduledTaskTable(NetBoxTable):
    pk = ToggleColumn(visible=True)
    device = tables.LinkColumn(
        verbose_name="Device",
    )
    scheduled_time = tables.TemplateColumn(
        verbose_name="Scheduled Time",
        template_code=SCHEDULED_TASK_TIME,
    )
    start_time = tables.TemplateColumn(
        verbose_name="Start Time",
        template_code=SCHEDULED_TASK_TIME,
    )
    end_time = tables.TemplateColumn(
        verbose_name="End Time",
        template_code=SCHEDULED_TASK_TIME,
    )
    task_type = tables.TemplateColumn(
        verbose_name="Task Type",
        template_code=SCHEDULED_TASK_TYPE,
        attrs={
            "td": {"align": "center"},
            "th": {"style": "text-align: center"},
        },
    )
    status = tables.TemplateColumn(
        verbose_name="Status",
        template_code=SCHEDULED_TASK_STATUS,
        attrs={
            "td": {"align": "center"},
            "th": {"style": "text-align: center"},
        },
    )
    confirmed = tables.TemplateColumn(
        verbose_name="ACK",
        template_code=SCHEDULED_TASK_CONFIRMED,
        orderable=True,
        attrs={
            "td": {"align": "center"},
            "th": {"style": "text-align: center"},
        },
    )
    job_id = tables.TemplateColumn(
        verbose_name="Job ID",
        template_code=SCHEDULED_TASK_JOB_ID,
    )
    actions = tables.TemplateColumn(
        template_code=SCHEDULED_TASK_ACTION,
        attrs={"td": {"class": "text-right noprint"}},
        verbose_name="",
    )

    class Meta(NetBoxTable.Meta):
        model = ScheduledTask
        fields = (
            "pk",
            "device",
            "scheduled_time",
            "start_time",
            "end_time",
            "task_type",
            "status",
            "confirmed",
            "job_id",
            "actions",
        )
        default_columns = (
            "pk",
            "device",
            "scheduled_time",
            "start_time",
            "end_time",
            "task_type",
            "status",
            "confirmed",
            "job_id",
            "actions",
        )


class ScheduledTaskBulkDeleteTable(ScheduledTaskTable):
    pk = ToggleColumn(visible=False)
    actions = None

    class Meta(NetBoxTable.Meta):
        model = ScheduledTask
        fields = (
            "device",
            "scheduled_time",
            "start_time",
            "end_time",
            "task_type",
            "status",
            "confirmed",
            "job_id",
        )
