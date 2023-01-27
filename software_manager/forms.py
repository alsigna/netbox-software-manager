from pathlib import Path

from dcim.models import Device, DeviceType, Manufacturer
from django import forms
from django.conf import settings
from netbox.forms import NetBoxModelFilterSetForm, NetBoxModelForm
from utilities.forms import (
    BOOLEAN_WITH_BLANK_CHOICES,
    BootstrapMixin,
    CommentField,
    DateTimePicker,
    DynamicModelMultipleChoiceField,
    MultipleChoiceField,
    StaticSelect,
    TagFilterField,
)

from .choices import TaskStatusChoices, TaskTransferMethod, TaskTypeChoices, ImageTypeChoices
from .models import GoldenImage, ScheduledTask, SoftwareImage

PLUGIN_SETTINGS = settings.PLUGINS_CONFIG.get("software_manager", dict())
CF_NAME_SW_VERSION = PLUGIN_SETTINGS.get("CF_NAME_SW_VERSION", "")
DEFAULT_TRANSFER_METHOD = PLUGIN_SETTINGS.get("DEFAULT_TRANSFER_METHOD", TaskTransferMethod.METHOD_FTP)
IMAGE_FOLDER = PLUGIN_SETTINGS.get("IMAGE_FOLDER", "")

IMAGE_FORMATS = ".bin,.tgz"


class ClearableFileInput(forms.ClearableFileInput):
    template_name = "software_manager/widgets/clearable_file_input.html"


class SoftwareImageEditForm(NetBoxModelForm):
    image = forms.FileField(
        required=False,
        label="Image",
        help_text="Image File, with .bin/.tgz extension",
        widget=ClearableFileInput(attrs={"accept": IMAGE_FORMATS}),
    )
    md5sum = forms.CharField(
        required=False,
        label="MD5 Checksum",
        help_text="Expected MD5 Checksum, ex: 0f58a02f3d3f1e1be8f509d2e5b58fb8",
    )

    supported_devicetypes = DynamicModelMultipleChoiceField(
        queryset=DeviceType.objects.all(),
        required=False,
        label="Supported Devices",
    )

    version = forms.CharField(
        required=True,
        label="Version",
        help_text="Verbose Software Version, ex: 15.5(3)M10",
    )
    comments = CommentField(
        label="Comments",
    )

    class Meta:
        model = SoftwareImage
        fields = [
            "image",
            "image_type",
            "supported_devicetypes",
            "md5sum",
            "version",
            "tags",
            "comments",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Once uploaded, image cannot be changed. Otherwise a lot of logical issues can be appeared.
        if self.instance.image_exists:
            self.fields["image"].widget.attrs["disabled"] = True
            self.fields["image"].initial = self.instance.image

    def clean(self):
        cleaned_data = super().clean()
        print(f"{cleaned_data=}")
        print(f"{self.instance=}")
        print(f"{self.instance.pk=}")
        image = cleaned_data.get("image", None)
        version = cleaned_data.get("version", None)
        if not version:
            raise forms.ValidationError(
                {"version": f"Version is requared"},
            )

        # if trying to upload image, but this filename already exists in DB
        if image and SoftwareImage.objects.filter(filename__iexact=image.name).exists():
            raise forms.ValidationError(
                {"image": f"Record '{image.name}' already exists. Contact with NetBox admins."},
            )

        # if trying to upload image, but this file already exists on a disk
        if image and Path(settings.MEDIA_ROOT, IMAGE_FOLDER, image.name).is_file():
            raise forms.ValidationError(
                {"image": f"File '{image.name}' already exists. Contact with NetBox admins."},
            )

        # if file not specified, version need to unique
        if (
            not image
            and SoftwareImage.objects.filter(version__iexact=version, image__exact="")
            .exclude(pk=self.instance.pk)
            .exists()
        ):
            raise forms.ValidationError(
                {"version": f"Version '{version}' without image already exists."},
            )


class SoftwareImageFilterForm(NetBoxModelFilterSetForm):
    filename = forms.CharField(
        required=False,
    )
    md5sum = forms.CharField(
        required=False,
        label="MD5",
    )
    version = forms.CharField(
        required=False,
        label="SW Version",
    )

    model = SoftwareImage
    tag = TagFilterField(SoftwareImage)
    fieldsets = (
        (None, ("q", "tag")),
        ("Exact Match", ("md5sum", "version")),
    )

    class Meta:
        model = SoftwareImage
        fields = (
            "filename",
            "md5sum",
            "version",
        )


class GoldenImageFilterForm(NetBoxModelFilterSetForm):
    manufacturer_id = DynamicModelMultipleChoiceField(
        queryset=Manufacturer.objects.all(),
        required=False,
        label="Manufacturer",
    )
    id = DynamicModelMultipleChoiceField(
        queryset=DeviceType.objects.all(),
        required=False,
        label="PID (Model)",
        query_params={"manufacturer_id": "$manufacturer_id"},
    )
    # TODO
    # software_image = DynamicModelMultipleChoiceField(
    #     queryset=SoftwareImage.objects.all(),
    #     required=False,
    #     label="Software Image",
    # )

    model = DeviceType
    fieldsets = ((None, ("q", "manufacturer_id", "id")),)

    class Meta:
        model = DeviceType
        fields = (
            "manufacturer_id",
            "id",
        )


class GoldenImageAddForm(BootstrapMixin, forms.ModelForm):
    device_pid = forms.CharField(
        required=True,
        label="Device PID",
    )
    sw = forms.ModelChoiceField(
        required=True,
        queryset=SoftwareImage.objects.all(),
        label="Image/Version",
    )

    class Meta:
        model = GoldenImage
        fields = ["device_pid", "sw"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["device_pid"].widget.attrs["readonly"] = True
        self.fields["device_pid"].initial = self.instance.pid


class ScheduledTaskCreateForm(BootstrapMixin, forms.Form):
    model = ScheduledTask
    pk = forms.ModelMultipleChoiceField(
        queryset=Device.objects.all(),
        widget=forms.MultipleHiddenInput(),
    )
    task_type = forms.ChoiceField(
        choices=TaskTypeChoices,
        required=True,
        label="Job Type",
        initial="",
        widget=StaticSelect(),
    )
    scheduled_time = forms.DateTimeField(
        label="Scheduled Time",
        required=False,
        widget=DateTimePicker(),
    )
    mw_duration = forms.IntegerField(
        required=True,
        initial=6,
        label="MW Duration, Hrs.",
    )

    start_now = ["scheduled_time"]

    transfer_method = forms.ChoiceField(
        choices=TaskTransferMethod,
        required=True,
        label="Transfer Method",
        initial=DEFAULT_TRANSFER_METHOD,
        widget=StaticSelect(),
    )

    class Meta:
        start_now = ["scheduled_time"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["mw_duration"].widget.attrs["max"] = 8
        self.fields["mw_duration"].widget.attrs["min"] = 1


class ScheduledTaskFilterForm(NetBoxModelFilterSetForm):
    status = MultipleChoiceField(
        choices=TaskStatusChoices,
        required=False,
    )
    task_type = MultipleChoiceField(
        choices=TaskTypeChoices,
        required=False,
    )
    confirmed = forms.NullBooleanField(
        required=False,
        label="Is Confirmed (ACK)",
        widget=StaticSelect(choices=BOOLEAN_WITH_BLANK_CHOICES),
    )
    scheduled_time_after = forms.DateTimeField(
        label="After",
        required=False,
        widget=DateTimePicker(),
    )
    scheduled_time_before = forms.DateTimeField(
        label="Before",
        required=False,
        widget=DateTimePicker(),
    )
    start_time_after = forms.DateTimeField(
        label="After",
        required=False,
        widget=DateTimePicker(),
    )
    start_time_before = forms.DateTimeField(
        label="Before",
        required=False,
        widget=DateTimePicker(),
    )
    end_time_after = forms.DateTimeField(
        label="After",
        required=False,
        widget=DateTimePicker(),
    )
    end_time_before = forms.DateTimeField(
        label="Before",
        required=False,
        widget=DateTimePicker(),
    )
    model = ScheduledTask
    fieldsets = (
        (None, ("q", "status", "task_type", "confirmed")),
        ("Scheduled Time", ("scheduled_time_after", "scheduled_time_before")),
        ("Start Time", ("start_time_after", "start_time_before")),
        ("End Time", ("end_time_after", "end_time_before")),
    )

    class Meta:
        model = ScheduledTask
        fields = (
            "status",
            "task_type",
            "confirmed",
            "scheduled_time_after",
            "scheduled_time_before",
            "start_time_after",
            "start_time_before",
            "end_time_after",
            "end_time_before",
        )
