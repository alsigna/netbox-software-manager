import pytz

from datetime import datetime
from django_rq import job, get_queue
from django.db.models import Count
from django.conf import settings

from .models import ScheduledTask
from .choices import TaskStatusChoices
from .upgrade import UpgradeDevice, UpgradeException


PLUGIN_SETTINGS = settings.PLUGINS_CONFIG.get('software_manager', dict())
UPGRADE_QUEUE = PLUGIN_SETTINGS.get('UPGRADE_QUEUE', '')


@job(UPGRADE_QUEUE)
def upgrade_device(task_id):

    def summary(status):
        q = get_queue(UPGRADE_QUEUE)
        total = ScheduledTask.objects.filter(scheduled_time=task.scheduled_time).count()
        field = 'status'
        stats = ScheduledTask.objects.filter(scheduled_time=task.scheduled_time).values(field).order_by(field).annotate(sum=Count(field))
        overall = ''
        for i in stats:
            overall = f'{overall} / {i["status"]} {i["sum"]}'
        overall = f'total {total}{overall}'
        device.info(f'Task ended with status "{status}"')
        device.info(f'Summary: {overall}')
        if q.count == 0:
            if q.started_job_registry.count == 1:
                device.info('All tasks have been completed.')
            else:
                device.info('No queued tasks were remained')
        else:
            device.info(f'Remained task: {q.count}. Taking the next one.')

    try:
        task = ScheduledTask.objects.get(id=task_id)
    except Exception:
        raise

    task.start_time = datetime.now().replace(microsecond=0, tzinfo=pytz.utc)
    task.status = TaskStatusChoices.STATUS_RUNNING
    task.save()

    try:
        device = UpgradeDevice(task)
        device.execute_task()
    except UpgradeException as e:
        if task.status == TaskStatusChoices.STATUS_SKIPPED:
            task.end_time = datetime.now().replace(microsecond=0, tzinfo=pytz.utc)
            task.confirmed = True
            task.save()
            summary(task.status)
            return f'Task was skipped. {e.reason}: {e.message}'
        task.end_time = datetime.now().replace(microsecond=0, tzinfo=pytz.utc)
        task.save()
        summary(task.status)
        raise
    except Exception:
        task.status = TaskStatusChoices.STATUS_FAILED
        task.message = 'Unknown Error'
        task.end_time = datetime.now().replace(microsecond=0, tzinfo=pytz.utc)
        task.save()
        summary(task.status)
        raise

    task.end_time = datetime.now().replace(microsecond=0, tzinfo=pytz.utc)
    task.status = TaskStatusChoices.STATUS_SUCCEEDED
    task.confirmed = True
    task.save()
    summary(task.status)

    return f'{task.device.name}/{task.task_type}: Done'
