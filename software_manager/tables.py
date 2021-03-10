import django_tables2 as tables

from django_tables2.utils import Accessor

from utilities.tables import BaseTable, ToggleColumn, ColoredLabelColumn, TagColumn
from dcim.models import DeviceType, Device
from tenancy.tables import COL_TENANT

from .models import ScheduledTask, SoftwareImage


SW_LIST_FILENAME = """
<i class="mdi mdi-file"></i>
<a href="{{ record.image.url }}" target="_blank">{{ record.filename }}</a>
"""

SW_LIST_SIZE = """
{{ record.image.size|filesizeformat }}
"""

SW_LIST_MD5SUM = """
{% if record.md5sum == record.md5sum_calculated %}
    <span class="label label-success" style="font-size: initial; font-family: monospace">{{ record.md5sum }}</span>
{% else %}
    <span class="label label-danger" style="font-size: initial; font-family: monospace">{{ record.md5sum|default:"&mdash;" }}</span>
{% endif %}
"""

SW_LIST_ACTION = """
<a href="{% url 'plugins:software_manager:software_edit' pk=record.pk %}" class="btn btn-xs btn-warning" title="Edit image">
    <i class="glyphicon glyphicon-pencil" aria-hidden="true"></i>
</a>
<a href="{% url 'plugins:software_manager:software_delete' pk=record.pk %}" class="btn btn-danger btn-xs" title="Delete image">
    <i class="glyphicon glyphicon-trash" aria-hidden="true"></i>
</a>
"""

GOLDEN_IMAGE_FILENAME = """
{{ record.golden_image.sw.filename|default:"&mdash;" }}
"""

GOLDEN_IMAGE_ACTION = """
{% if record.golden_image %}
    <a href="{% url 'plugins:software_manager:golden_image_edit' pk=record.golden_image.pk %}" class="btn btn-xs btn-warning" title="Edit Image">
        <i class="glyphicon glyphicon-pencil" aria-hidden="true"></i>
    </a>
    <a href="{% url 'plugins:software_manager:golden_image_delete' pk=record.golden_image.pk %}" class="btn btn-danger btn-xs" title="Clear image">
        <i class="glyphicon glyphicon-trash" aria-hidden="true"></i>
    </a>
{% else %}
    <a href="{% url 'plugins:software_manager:golden_image_add' pid_pk=record.pk %}" class="btn btn-xs btn-warning" title="Add Image">
        <i class="glyphicon glyphicon-pencil" aria-hidden="true"></i>
    </a>
    <button class="btn btn-danger btn-xs" title="Clear image" disabled="disabled">
        <i class="glyphicon glyphicon-trash" aria-hidden="true"></i>
    </button>
{% endif %}
"""

GOLDEN_IMAGE_MD5SUM = """
{% if record.golden_image.sw.md5sum == record.golden_image.sw.md5sum_calculated %}
    <span class="label label-success" style="font-size: initial; font-family: monospace">{{ record.golden_image.sw.md5sum }}</span>
{% else %}
    <span class="label label-danger" style="font-size: initial; font-family: monospace">{{ record.golden_image.sw.md5sum|default:"&mdash;" }}</span>
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

UPGRADE_DEVICE_LINK = """
<a href="{% url 'dcim:device' pk=record.pk %}">
    {{ record.name|default:'<span class="label label-info">UNKNOWN DEVICE</span>' }}
</a>
"""

UPGRADE_TARGET_SOFTWARE = """
{{ record.device_type.golden_image.sw.version|default:"&mdash;" }}
"""

UPGRADE_CURRENT_SOFTWARE = """
{% if record|get_current_version %}
    {% if record|get_current_version == record.device_type.golden_image.sw.version %}
        <span class="label label-success" style="font-size:small">{{ record|get_current_version }}</span>
    {% else %}
        <span class="label label-warning" style="font-size:small">{{ record|get_current_version }}</span>
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
    <span class="label label-info">Upload</span>
{% elif record.task_type == 'upgrade' %}
    <span class="label label-primary">Upgrade</span>
{% else %}
    <span class="label label-default">Unknown</span>
{% endif %}
"""

SCHEDULED_TASK_STATUS = """
{% if record.status == 'succeeded' %}
    <span class="label label-success" title="Task Finished Successfully">Succeeded</span>
{% elif record.status == 'skipped' %}
    <span class="label label-warning" title="{{ record.message }}">Skipped</span>
{% elif record.status == 'failed' %}
    <span class="label label-danger" title="{{ record.message }}">Failed</span>
{% elif record.status == 'scheduled' %}
    <span class="label label-default" title="Task Scheduled">Scheduled</span>
{% elif record.status == 'running' %}
    <span class="label label-info" title="Task is Running">Running</span>
{% else %}
    <span class="label label-default" title="Unknown Status">Unknown</span>
{% endif %}
"""

SCHEDULED_TASK_ACTION = """
<a href="{% url 'plugins:software_manager:scheduled_task_delete' pk=record.pk %}" class="btn btn-danger btn-xs" title="Delete Task">
    <i class="glyphicon glyphicon-trash" aria-hidden="true"></i>
</a>
"""

SCHEDULED_TASK_CONFIRMED = """
{% if record.confirmed %}
    <button type="submit" class="btn btn-xs btn-success" name="_confirm" value="{{ record.pk }}">
        <span class="mdi mdi-check-bold" aria-hidden="true"></span>
    </button>
{% else %}
    <button type="submit" class="btn btn-xs btn-danger" name="_confirm" value="{{ record.pk }}">
        <span class="mdi mdi-close-thick" aria-hidden="true"></span>
    </button>
{% endif %}
"""

SCHEDULED_TASK_JOB_ID = """
<a href="{% url 'plugins:software_manager:scheduled_task_info' pk=record.pk %}">{{ record.job_id|cut_job_id }}</a>
"""


class SoftwareListTable(BaseTable):
    filename = tables.TemplateColumn(
        verbose_name='Filename',
        template_code=SW_LIST_FILENAME,
        orderable=False,
    )
    version = tables.Column(
        verbose_name='Version',
        orderable=False,
    )
    size = tables.TemplateColumn(
        verbose_name='Size',
        template_code=SW_LIST_SIZE,
        orderable=False,
    )
    md5sum = tables.TemplateColumn(
        verbose_name='MD5 Checksum',
        template_code=SW_LIST_MD5SUM,
        orderable=False,
    )
    actions = tables.TemplateColumn(
        template_code=SW_LIST_ACTION,
        attrs={'td': {'class': 'text-right noprint'}},
        verbose_name='',
    )

    class Meta(BaseTable.Meta):
        model = SoftwareImage
        fields = ('filename', 'version', 'size', 'md5sum', 'actions')
        sequence = ('filename', 'version', 'size', 'md5sum', 'actions')


class GoldenImageListTable(BaseTable):
    model = tables.LinkColumn(
        viewname='dcim:devicetype',
        args=[Accessor('pk')],
        verbose_name='Device PID'
    )
    image = tables.TemplateColumn(
        verbose_name='Image File',
        template_code=GOLDEN_IMAGE_FILENAME,
        orderable=False,
    )
    version = tables.Column(
        verbose_name='Version',
        accessor='golden_image.sw.version',
        orderable=False,
    )
    md5sum = tables.TemplateColumn(
        verbose_name='MD5 Checksum',
        template_code=GOLDEN_IMAGE_MD5SUM,
        orderable=False,
    )
    progress = tables.TemplateColumn(
        template_code=GOLDEN_IMAGE_PROGRESS_GRAPH,
        orderable=False,
        verbose_name='Progress',
    )
    actions = tables.TemplateColumn(
        template_code=GOLDEN_IMAGE_ACTION,
        attrs={'td': {'class': 'text-right noprint'}},
        verbose_name=''
    )

    class Meta(BaseTable.Meta):
        model = DeviceType
        fields = ('model', 'version', 'image', 'md5sum', 'progress', 'actions')


class UpgradeDeviceListTable(BaseTable):
    pk = ToggleColumn()
    name = tables.TemplateColumn(
        order_by=('name',),
        template_code=UPGRADE_DEVICE_LINK
    )
    t_sw = tables.TemplateColumn(
        verbose_name='Target Version',
        template_code=UPGRADE_TARGET_SOFTWARE,
        orderable=False,
    )
    c_sw = tables.TemplateColumn(
        verbose_name='Curent Version',
        template_code=UPGRADE_CURRENT_SOFTWARE,
        orderable=False,
    )
    tenant = tables.TemplateColumn(
        template_code=COL_TENANT
    )
    device_role = ColoredLabelColumn(
        verbose_name='Role'
    )
    device_type = tables.LinkColumn(
        verbose_name='Device Type',
        text=lambda record: record.device_type.model
    )
    tags = TagColumn(
        url_name='dcim:device_list'
    )

    class Meta(BaseTable.Meta):
        model = Device
        fields = ('pk', 'name', 't_sw', 'c_sw', 'tenant', 'device_role', 'device_type', 'tags')


class ScheduledTaskTable(BaseTable):
    pk = ToggleColumn()
    device = tables.LinkColumn(
        verbose_name='Device',
    )
    scheduled_time = tables.TemplateColumn(
        verbose_name='Scheduled Time',
        template_code=SCHEDULED_TASK_TIME,
    )
    start_time = tables.TemplateColumn(
        verbose_name='Start Time',
        template_code=SCHEDULED_TASK_TIME,
    )
    end_time = tables.TemplateColumn(
        verbose_name='End Time',
        template_code=SCHEDULED_TASK_TIME,
    )
    task_type = tables.TemplateColumn(
        verbose_name='Task Type',
        template_code=SCHEDULED_TASK_TYPE,
        attrs={
            'td': {'align': 'center'},
            'th': {'style': 'text-align: center'},
        },
    )
    status = tables.TemplateColumn(
        verbose_name='Status',
        template_code=SCHEDULED_TASK_STATUS,
        attrs={
            'td': {'align': 'center'},
            'th': {'style': 'text-align: center'},
        },
    )
    confirmed = tables.TemplateColumn(
        verbose_name='ACK',
        template_code=SCHEDULED_TASK_CONFIRMED,
        orderable=True,
        attrs={
            'td': {'align': 'center'},
            'th': {'style': 'text-align: center'},
        },
    )
    job_id = tables.TemplateColumn(
        verbose_name='Job ID',
        template_code=SCHEDULED_TASK_JOB_ID,
    )
    actions = tables.TemplateColumn(
        template_code=SCHEDULED_TASK_ACTION,
        attrs={'td': {'class': 'text-right noprint'}},
        verbose_name='',
    )

    class Meta(BaseTable.Meta):
        model = ScheduledTask
        fields = ('pk', 'device', 'scheduled_time', 'start_time', 'end_time', 'task_type', 'status', 'confirmed', 'job_id', 'actions')
        sequence = ('pk', 'device', 'scheduled_time', 'start_time', 'end_time', 'task_type', 'status', 'confirmed', 'job_id', 'actions')
