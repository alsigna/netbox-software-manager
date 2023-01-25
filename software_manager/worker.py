from datetime import datetime

import pytz
from django.conf import settings
from django.db.models import Count
from django_rq import get_queue, job

from .choices import TaskStatusChoices
from .models import ScheduledTask
from .task_exceptions import TaskException
from .task_executor import TaskExecutor

PLUGIN_SETTINGS = settings.PLUGINS_CONFIG.get("software_manager", dict())
UPGRADE_QUEUE = PLUGIN_SETTINGS.get("UPGRADE_QUEUE", "")


@job(UPGRADE_QUEUE)
def upgrade_device(task_id):
    def add_summary(status):
        queue = get_queue(UPGRADE_QUEUE)
        total = ScheduledTask.objects.filter(scheduled_time=task.scheduled_time).count()
        field = "status"
        stats = (
            ScheduledTask.objects.filter(scheduled_time=task.scheduled_time)
            .values(field)
            .order_by(field)
            .annotate(sum=Count(field))
        )
        overall = ""
        for i in stats:
            overall = f'{overall} / {i["status"]} {i["sum"]}'
        overall = f"total {total}{overall}"
        executor.info(f'Task ended with status "{status}"')
        executor.info(f"Summary: {overall}")
        if queue.count == 0:
            if queue.started_job_registry.count == 1:
                executor.info("All tasks have been completed.")
            else:
                executor.info("No queued tasks were remained")
        else:
            executor.info(f"Remained task: {queue.count}. Taking the next one.")

    try:
        task = ScheduledTask.objects.get(id=task_id)
    except Exception:
        raise

    task.start_time = datetime.now().replace(microsecond=0).astimezone(pytz.utc)
    task.status = TaskStatusChoices.STATUS_RUNNING
    task.save()

    executor = TaskExecutor(task)
    try:
        executor.execute_task()
    except TaskException as exc:
        if task.status == TaskStatusChoices.STATUS_SKIPPED:
            task.end_time = datetime.now().replace(microsecond=0).astimezone(pytz.utc)
            task.confirmed = True
            task.save()
            add_summary(task.status)
            return f"Task was skipped. {exc.reason}: {exc.message}"
        task.end_time = datetime.now().replace(microsecond=0).astimezone(pytz.utc)
        task.save()
        add_summary(task.status)
        raise
    except Exception:
        task.status = TaskStatusChoices.STATUS_FAILED
        task.message = "Unknown Error"
        task.end_time = datetime.now().replace(microsecond=0).astimezone(pytz.utc)
        task.save()
        add_summary(task.status)
        raise

    task.end_time = datetime.now().replace(microsecond=0).astimezone(pytz.utc)
    task.status = TaskStatusChoices.STATUS_SUCCEEDED
    task.confirmed = True
    task.save()
    add_summary(task.status)

    return f"{task.device.name}/{task.task_type}: Done"
