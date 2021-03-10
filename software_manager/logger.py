import pytz
import logging
import os

from datetime import datetime
from django.conf import settings


PLUGIN_SETTINGS = settings.PLUGINS_CONFIG.get('software_manager', dict())
UPGRADE_LOG_FILE = PLUGIN_SETTINGS.get('UPGRADE_LOG_FILE', '')
TIME_ZONE = os.environ.get('TIME_ZONE', 'UTC')


def CustomTimeZone(*args):
    utc_dt = pytz.utc.localize(datetime.utcnow())
    my_tz = pytz.timezone(TIME_ZONE)
    converted = utc_dt.astimezone(my_tz)
    return converted.timetuple()


log_f = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        '%Y-%m-%d %H:%M:%S'
)
log_fh = logging.FileHandler(UPGRADE_LOG_FILE)
log_fh.setFormatter(log_f)
log_fh.formatter.converter = CustomTimeZone
log = logging.getLogger('upgrade')
log.setLevel(logging.INFO)
log.addHandler(log_fh)
