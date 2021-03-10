from django import forms
from django.contrib.contenttypes.models import ContentType
from django.utils.safestring import mark_safe
from django.conf import settings

from dcim.models import DeviceType, Device, DeviceRole
from utilities.forms import (
    BootstrapMixin, DynamicModelMultipleChoiceField, TagFilterField, DateTimePicker,
    StaticSelect2, StaticSelect2Multiple, BOOLEAN_WITH_BLANK_CHOICES,
)
from extras.models import CustomField
from tenancy.models import Tenant

from .choices import TaskTypeChoices, TaskStatusChoices
from .models import SoftwareImage, GoldenImage, ScheduledTask


PLUGIN_SETTINGS = settings.PLUGINS_CONFIG.get('software_manager', dict())
CF_NAME_SW_VERSION = PLUGIN_SETTINGS.get('CF_NAME_SW_VERSION', '')


class SoftwareImageAddForm(BootstrapMixin, forms.ModelForm):
    image = forms.FileField(
        required=True,
        label='IOS',
        help_text='IOS Image File',
    )
    md5sum = forms.CharField(
        required=True,
        label='MD5 Checksum',
        help_text='Expected MD5 Checksum, ex: 0f58a02f3d3f1e1be8f509d2e5b58fb8',
    )
    version = forms.CharField(
        required=True,
        label='Version',
        help_text='Verbose Software Version, ex: 15.5(3)M10',
    )

    class Meta:
        model = SoftwareImage
        fields = ['image', 'md5sum', 'version']


class GoldenImageAddForm(BootstrapMixin, forms.ModelForm):
    device_pid = forms.CharField(
        required=True,
        label='Device PID',
    )
    sw = forms.ModelChoiceField(
        required=True,
        queryset=SoftwareImage.objects.all(),
        label='Device Image File',
    )

    class Meta:
        model = GoldenImage
        fields = [
            'device_pid', 'sw'
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['device_pid'].widget.attrs['readonly'] = True
        self.fields['device_pid'].initial = self.instance.pid


class ScheduledTaskCreateForm(BootstrapMixin, forms.Form):
    model = ScheduledTask
    pk = forms.ModelMultipleChoiceField(
        queryset=Device.objects.all(),
        widget=forms.MultipleHiddenInput()
    )
    task_type = forms.ChoiceField(
        choices=TaskTypeChoices,
        required=True,
        label='Job Type',
        initial='',
        widget=StaticSelect2()
    )
    scheduled_time = forms.DateTimeField(
        label='Scheduled Time',
        required=False,
        widget=DateTimePicker(),
    )
    mw_duration = forms.IntegerField(
        required=True,
        initial=6,
        label='MW Duration, Hrs.',
    )

    start_now = ['scheduled_time']

    class Meta:
        start_now = ['scheduled_time']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['mw_duration'].widget.attrs['max'] = 8
        self.fields['mw_duration'].widget.attrs['min'] = 1


class ScheduledTaskFilterForm(BootstrapMixin, forms.ModelForm):
    model = ScheduledTask
    q = forms.CharField(
        required=False,
        label='Search'
    )
    task_type = forms.MultipleChoiceField(
        label='Type',
        choices=TaskTypeChoices,
        required=False,
        widget=StaticSelect2Multiple()
    )
    status = forms.MultipleChoiceField(
        label='Status',
        choices=TaskStatusChoices,
        required=False,
        widget=StaticSelect2Multiple()
    )
    confirmed = forms.NullBooleanField(
        required=False,
        label='Is Confirmed (ACK)',
        widget=StaticSelect2(choices=BOOLEAN_WITH_BLANK_CHOICES)
    )
    scheduled_time_after = forms.DateTimeField(
        label=mark_safe('<br/>Scheduled After'),
        required=False,
        widget=DateTimePicker()
    )
    scheduled_time_before = forms.DateTimeField(
        label='Scheduled Before',
        required=False,
        widget=DateTimePicker()
    )
    start_time_after = forms.DateTimeField(
        label=mark_safe('<br/>Started After'),
        required=False,
        widget=DateTimePicker()
    )
    start_time_before = forms.DateTimeField(
        label='Started Before',
        required=False,
        widget=DateTimePicker()
    )
    end_time_after = forms.DateTimeField(
        label=mark_safe('<br/>Ended After'),
        required=False,
        widget=DateTimePicker()
    )
    end_time_before = forms.DateTimeField(
        label='Ended Before',
        required=False,
        widget=DateTimePicker()
    )

    class Meta:
        model = ScheduledTask
        fields = [
            'q', 'task_type', 'status', 'confirmed',
            'scheduled_time_after', 'scheduled_time_before',
            'start_time_after', 'start_time_before',
            'end_time_after', 'end_time_before',
        ]


class CustomFieldVersionFilterForm(forms.Form):
    def __init__(self, *args, **kwargs):
        self.obj_type = ContentType.objects.get_for_model(self.model)
        super().__init__(*args, **kwargs)
        custom_fields = CustomField.objects.get(content_types=self.obj_type, name=CF_NAME_SW_VERSION)
        field_name = 'cf_{}'.format(custom_fields.name)
        self.fields[field_name] = custom_fields.to_form_field(set_initial=True, enforce_required=False)


class UpgradeDeviceFilterForm(BootstrapMixin, CustomFieldVersionFilterForm):
    model = Device
    field_order = ['q', 'role', 'tenant', 'device_type_id', 'tag', 'target_sw']
    q = forms.CharField(
        required=False,
        label='Search'
    )
    tenant = DynamicModelMultipleChoiceField(
        queryset=Tenant.objects.all(),
        to_field_name='slug',
        required=False,
    )
    role = DynamicModelMultipleChoiceField(
        queryset=DeviceRole.objects.all(),
        to_field_name='slug',
        required=False,
    )
    device_type_id = DynamicModelMultipleChoiceField(
        queryset=DeviceType.objects.all(),
        required=False,
        label='Model',
        display_field='model',
    )
    target_sw = forms.CharField(
        label='Target SW',
        required=False,
        help_text='Target SW Version',
    )
    tag = TagFilterField(model)
