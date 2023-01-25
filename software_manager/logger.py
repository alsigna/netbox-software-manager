import logging
from datetime import datetime

import pytz
from django.conf import settings

from .models import ScheduledTask

PLUGIN_SETTINGS = settings.PLUGINS_CONFIG.get("software_manager", dict())
UPGRADE_LOG_FILE = PLUGIN_SETTINGS.get("UPGRADE_LOG_FILE", "")


def CustomTimeZone(*args):
    utc_dt = pytz.utc.localize(datetime.utcnow())
    my_tz = pytz.timezone(settings.TIME_ZONE)
    converted = utc_dt.astimezone(my_tz)
    return converted.timetuple()


log_f = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s", "%Y-%m-%d %H:%M:%S")
log_fh = logging.FileHandler(UPGRADE_LOG_FILE)
log_fh.setFormatter(log_f)
log_fh.formatter.converter = CustomTimeZone
log = logging.getLogger("upgrade")
log.setLevel(logging.DEBUG)
log.addHandler(log_fh)


class TaskLoggerMixIn:
    def __init__(self, task: ScheduledTask) -> None:
        self.task = task
        if task.device is not None:
            hostname = task.device.name
        else:
            hostname = "unknown-device"
        self.log_id = f"{task.job_id} - {hostname}"

    def debug(self, msg: str) -> None:
        log.debug(f"{self.log_id} - {msg}")
        self.task.log += (
            f'{datetime.now(pytz.timezone(settings.TIME_ZONE)).strftime("%Y-%m-%d %H:%M:%S")} - DEBUG - {msg}\n'
        )
        self.task.save()

    def info(self, msg: str) -> None:
        log.info(f"{self.log_id} - {msg}")
        self.task.log += (
            f'{datetime.now(pytz.timezone(settings.TIME_ZONE)).strftime("%Y-%m-%d %H:%M:%S")} - INFO - {msg}\n'
        )
        self.task.save()

    def warning(self, msg: str) -> None:
        log.warning(f"{self.log_id} - {msg}")
        self.task.log += (
            f'{datetime.now(pytz.timezone(settings.TIME_ZONE)).strftime("%Y-%m-%d %H:%M:%S")} - WARNING - {msg}\n'
        )
        self.task.save()

    def error(self, msg: str) -> None:
        log.error(f"{self.log_id} - {msg}")
        self.task.log += (
            f'{datetime.now(pytz.timezone(settings.TIME_ZONE)).strftime("%Y-%m-%d %H:%M:%S")} - ERROR - {msg}\n'
        )
        self.task.save()
