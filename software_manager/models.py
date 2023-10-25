import hashlib
from pathlib import Path

from dcim.models import Device, DeviceType
from django.conf import settings
from django.core.validators import FileExtensionValidator
from django.db import models
from django.db.models import Q
from django.urls import reverse
from django_rq import get_queue
from netbox.models import NetBoxModel
from rq.exceptions import NoSuchJobError
from rq.job import Job
from utilities.querysets import RestrictedQuerySet

from .choices import TaskFailReasonChoices, TaskStatusChoices, TaskTransferMethod, TaskTypeChoices, ImageTypeChoices

PLUGIN_SETTINGS = settings.PLUGINS_CONFIG.get("software_manager", dict())
CF_NAME_SW_VERSION = PLUGIN_SETTINGS.get("CF_NAME_SW_VERSION", "")
FTP_USERNAME = PLUGIN_SETTINGS.get("FTP_USERNAME", "")
IMAGE_FOLDER = PLUGIN_SETTINGS.get("IMAGE_FOLDER", "")
UPGRADE_QUEUE = PLUGIN_SETTINGS.get("UPGRADE_QUEUE", "")


class SoftwareImage(NetBoxModel):
    image = models.FileField(
        upload_to=f"{IMAGE_FOLDER}",
        validators=[FileExtensionValidator(allowed_extensions=["bin","tgz"])],
        null=True,
        blank=True,
    )

    image_type = models.CharField(
        max_length=255,
        choices=ImageTypeChoices,
        default=ImageTypeChoices.TYPE_JUNOS,
    )


    supported_devicetypes = models.ManyToManyField(
        to=DeviceType,
        related_name="software_images",
    )
        
    md5sum = models.CharField(
        max_length=36,
        blank=True,
    )
    md5sum_calculated = models.CharField(
        max_length=36,
        blank=True,
    )
    version = models.CharField(
        max_length=32,
        blank=True,
    )
    filename = models.CharField(
        max_length=256,
        blank=True,
    )
    comments = models.TextField(
        blank=True,
    )

    class Meta:
        ordering = ["-filename", "-version"]

    def save(self, *args, **kwargs) -> None:
        if not self.image_exists:
            self.filename = ""
            self.md5sum_calculated = ""
            self.md5sum = ""
            super().save(*args, **kwargs)
            return

        self.filename = self.image.name.rsplit("/", 1)[-1]

        md5 = hashlib.md5()
        for chunk in self.image.chunks():
            md5.update(chunk)
        self.md5sum_calculated = md5.hexdigest()
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs) -> tuple[int, dict[str, int]]:
        if self.image_exists:
            Path(self.image.path).unlink(missing_ok=True)
        return super().delete(*args, **kwargs)

    def __str__(self) -> str:
        if self.image_exists:
            return self.image.name.rsplit("/", 1)[-1]
        else:
            return f"{self.version} (no image)"

    @property
    def image_exists(self) -> bool:
        return bool(self.image.name)

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}: {str(self)}>"

    def get_absolute_url(self) -> str:
        return reverse("plugins:software_manager:softwareimage", kwargs={"pk": self.pk})


class GoldenImage(NetBoxModel):
    pid = models.OneToOneField(
        to=DeviceType,
        on_delete=models.CASCADE,
        related_name="golden_image",
    )
    sw = models.ForeignKey(
        to=SoftwareImage,
        on_delete=models.CASCADE,
        blank=True,
        null=True,
    )

    class Meta:
        ordering = ["pid"]
        verbose_name = "Golden Image"

    def __str__(self) -> str:
        return f"{self.pid.model} - {self.sw}"

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}: {str(self)}>"

    def get_progress(self) -> float:
        total = self.pid.instances.count()
        if total == 0:
            return 0.0
        upgraded = Device.objects.filter(
            **{f"custom_field_data__{CF_NAME_SW_VERSION}": self.sw.version},
            device_type=self.pid,
        ).count()
        return round(upgraded / total * 100, 2)


class ScheduledTaskQuerySet(RestrictedQuerySet):
    def delete(self):
        exclude_list = []
        queue = get_queue(UPGRADE_QUEUE)
        for i in self:
            try:
                j = Job.fetch(i.job_id, queue.connection)
                if not j.is_started:
                    j.delete()
                else:
                    exclude_list.append(i.job_id)
            except NoSuchJobError:
                pass
        return super(ScheduledTaskQuerySet, self.exclude(Q(job_id__in=exclude_list))).delete()


class ScheduledTaskManager(models.Manager):
    def get_queryset(self):
        return ScheduledTaskQuerySet(self.model, using=self._db)


class ScheduledTask(NetBoxModel):
    device = models.ForeignKey(
        to=Device,
        on_delete=models.SET_NULL,
        null=True,
    )
    task_type = models.CharField(
        max_length=255,
        choices=TaskTypeChoices,
        default=TaskTypeChoices.TYPE_UPLOAD,
    )
    job_id = models.CharField(
        max_length=255,
        blank=True,
    )
    status = models.CharField(
        max_length=255,
        choices=TaskStatusChoices,
        default=TaskStatusChoices.STATUS_UNKNOWN,
    )
    message = models.CharField(
        max_length=512,
        blank=True,
    )
    fail_reason = models.CharField(
        max_length=255,
        choices=TaskFailReasonChoices,
        default=TaskFailReasonChoices.FAIL_UNKNOWN,
    )
    confirmed = models.BooleanField(
        default=False,
    )
    scheduled_time = models.DateTimeField(
        null=True,
    )
    start_time = models.DateTimeField(
        null=True,
    )
    end_time = models.DateTimeField(
        null=True,
    )
    mw_duration = models.PositiveIntegerField(
        null=True,
    )
    log = models.TextField(
        blank=True,
    )
    user = models.CharField(
        max_length=255,
        blank=True,
    )
    transfer_method = models.CharField(
        max_length=8,
        choices=TaskTransferMethod,
        default=TaskTransferMethod.METHOD_FTP,
    )

    objects = ScheduledTaskManager()

    def __str__(self):
        if not self.device:
            return "unknown"
        else:
            return f"{self.device}: {self.job_id}"

    def delete(self):
        queue = get_queue(UPGRADE_QUEUE)
        try:
            j = Job.fetch(self.job_id, queue.connection)
            if not j.is_started:
                j.delete()
                return super().delete()
        except NoSuchJobError:
            return super().delete()

    def get_absolute_url(self) -> str:
        return reverse("plugins:software_manager:scheduledtask", kwargs={"pk": self.pk})

    class Meta:
        ordering = [
            "-scheduled_time",
            "-start_time",
            "-end_time",
            "job_id",
        ]
        verbose_name = "Scheduled Task"
