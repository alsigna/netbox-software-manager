import os
import hashlib

from django.db import models
from django.db.models import Q
from django.core.validators import FileExtensionValidator
from django.conf import settings
from django_rq import get_scheduler
from rq.job import Job
from rq.exceptions import NoSuchJobError

from dcim.models import Device
from utilities.querysets import RestrictedQuerySet

from .choices import TaskTypeChoices, TaskStatusChoices, TaskFailReasonChoices

PLUGIN_SETTINGS = settings.PLUGINS_CONFIG.get('software_manager', dict())
CF_NAME_SW_VERSION = PLUGIN_SETTINGS.get('CF_NAME_SW_VERSION', '')
FTP_USERNAME = PLUGIN_SETTINGS.get('FTP_USERNAME', '')


class SoftwareImage(models.Model):
    timestamp = models.DateTimeField(auto_now_add=True)
    image = models.FileField(
        upload_to=f'{FTP_USERNAME}/', unique=True, validators=[FileExtensionValidator(allowed_extensions=['bin'])]
    )
    md5sum = models.CharField(max_length=36, blank=True)
    md5sum_calculated = models.CharField(max_length=36, blank=True)
    version = models.CharField(max_length=32, blank=True)
    filename = models.CharField(max_length=255, blank=True)

    objects = RestrictedQuerySet.as_manager()

    class Meta:
        ordering = ['-filename']

    def save(self, *args, **kwargs):
        self.filename = self.image.name.rsplit('/', 1)[-1]
        if self.pk:
            super(SoftwareImage, self).save(*args, **kwargs)
        else:
            if not SoftwareImage.objects.filter(filename=self.filename).count() and not os.path.exists(
                os.path.join(os.path.dirname(self.image.path), FTP_USERNAME, self.filename)
            ):
                md5 = hashlib.md5()
                for chunk in self.image.chunks():
                    md5.update(chunk)
                self.md5sum_calculated = md5.hexdigest()
                super(SoftwareImage, self).save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        if os.path.isfile(self.image.path):
            os.remove(self.image.path)
        super(SoftwareImage, self).delete(*args, **kwargs)

    def __str__(self):
        return self.image.name.rsplit('/', 1)[-1]


class GoldenImage(models.Model):
    timestamp = models.DateTimeField(auto_now_add=True)
    pid = models.OneToOneField(to='dcim.DeviceType', on_delete=models.CASCADE, related_name='golden_image')
    sw = models.ForeignKey(to='SoftwareImage', on_delete=models.CASCADE, blank=True, null=True)

    objects = RestrictedQuerySet.as_manager()

    class Meta:
        ordering = ['pid']

    def __str__(self):
        return f'{self.pid.model}: {self.sw}'

    def get_progress(self):
        total = self.pid.instances.count()
        if total == 0:
            return 0
        upgraded = Device.objects.filter(
            **{f'custom_field_data__{CF_NAME_SW_VERSION}': self.sw.version},
            device_type=self.pid,
        ).count()
        return round(upgraded / total * 100, 2)


class ScheduledTaskQuerySet(RestrictedQuerySet):
    def delete(self):
        exclude_list = []
        scheduler = get_scheduler('default')
        for i in self:
            try:
                j = Job.fetch(i.job_id, scheduler.connection)
                if not j.is_started:
                    j.delete()
                    scheduler.cancel(j)
                else:
                    exclude_list.append(i.job_id)
            except NoSuchJobError:
                pass
        return super(ScheduledTaskQuerySet, self.exclude(Q(job_id__in=exclude_list))).delete()


class ScheduledTaskManager(models.Manager):
    def get_queryset(self):
        return ScheduledTaskQuerySet(self.model, using=self._db)


class ScheduledTask(models.Model):
    timestamp = models.DateTimeField(auto_now_add=True)
    device = models.ForeignKey(to='dcim.Device', on_delete=models.SET_NULL, blank=True, null=True)
    task_type = models.CharField(max_length=255, choices=TaskTypeChoices, default=TaskTypeChoices.TYPE_UPLOAD)
    job_id = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=255, choices=TaskStatusChoices, default=TaskStatusChoices.STATUS_UNKNOWN)
    message = models.CharField(max_length=511, blank=True)
    fail_reason = models.CharField(
        max_length=255, choices=TaskFailReasonChoices, default=TaskFailReasonChoices.FAIL_UNKNOWN
    )
    confirmed = models.BooleanField(default=False)
    scheduled_time = models.DateTimeField(blank=True)
    start_time = models.DateTimeField(null=True)
    end_time = models.DateTimeField(null=True)
    mw_duration = models.PositiveIntegerField(blank=True)
    log = models.TextField(blank=True)
    user = models.CharField(max_length=255, blank=True)

    objects = ScheduledTaskManager()

    def __str__(self):
        if not self.device:
            return ''
        else:
            return f'{self.device}: {self.job_id}'

    def delete(self):
        scheduler = get_scheduler('default')
        try:
            j = Job.fetch(self.job_id, scheduler.connection)
            if not j.is_started:
                j.delete()
                scheduler.cancel(j)
                return super().delete()
        except NoSuchJobError:
            return super().delete()

    class Meta:
        ordering = ['-scheduled_time', '-start_time', '-end_time', 'job_id']
