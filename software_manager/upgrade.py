import re
import socket
import time
import pytz
import os

from django_rq import get_queue
# from django_rq import job, get_queue
from django.conf import settings
from datetime import timedelta
# from random import randint
from scrapli.driver.core import IOSXEDriver
from scrapli.exceptions import ScrapliAuthenticationFailed, ScrapliConnectionError, ScrapliTimeout
from datetime import datetime

from .logger import log
from .choices import TaskStatusChoices, TaskFailReasonChoices, TaskTypeChoices
from .models import ScheduledTask
from .custom_exceptions import UpgradeException


PLUGIN_SETTINGS = settings.PLUGINS_CONFIG.get('software_manager', dict())
CF_NAME_SW_VERSION = PLUGIN_SETTINGS.get('CF_NAME_SW_VERSION', '')
UPGRADE_QUEUE = PLUGIN_SETTINGS.get('UPGRADE_QUEUE', '')
UPGRADE_THRESHOLD = PLUGIN_SETTINGS.get('UPGRADE_THRESHOLD', '')
UPGRADE_MAX_ATTEMPTS_AFTER_RELOAD = PLUGIN_SETTINGS.get('UPGRADE_MAX_ATTEMPTS_AFTER_RELOAD', '')
UPGRADE_SECONDS_BETWEEN_ATTEMPTS = PLUGIN_SETTINGS.get('UPGRADE_SECONDS_BETWEEN_ATTEMPTS', '')
DEVICE_USERNAME = PLUGIN_SETTINGS.get('DEVICE_USERNAME', '')
DEVICE_PASSWORD = PLUGIN_SETTINGS.get('DEVICE_PASSWORD', '')
FTP_USERNAME = PLUGIN_SETTINGS.get('FTP_USERNAME', '')
FTP_PASSWORD = PLUGIN_SETTINGS.get('FTP_PASSWORD', '')
FTP_SERVER = PLUGIN_SETTINGS.get('FTP_SERVER', '')
TIME_ZONE = os.environ.get('TIME_ZONE', 'UTC')


class UpgradeDevice:
    def __init__(self, task):
        self.task = task
        self.log_id = f'{task.job_id} - {task.device.name}'
        self.device = {
            'auth_username': DEVICE_USERNAME,
            'auth_password': DEVICE_PASSWORD,
            'auth_strict_key': False,
            # 'ssh_config_file':'/var/lib/unit/.ssh/config',
            # 'ssh_config_file':'/root/.ssh/config',
            'port': 22,
            'timeout_socket': 5,
            'transport': 'paramiko',
        }
        if task.device.primary_ip:
            self.device['host'] = str(task.device.primary_ip.address.ip)
        else:
            msg = 'No primary (mgmt) address'
            self.warning(msg)
            self.skip_task(msg, TaskFailReasonChoices.FAIL_CHECK)

    def debug(self, msg):
        log.debug(f'{self.log_id} - {msg}')
        self.task.log += f'{datetime.now(pytz.timezone(TIME_ZONE)).strftime("%Y-%m-%d %H:%M:%S")} - DEBUG - {msg}\n'
        self.task.save()

    def info(self, msg):
        log.info(f'{self.log_id} - {msg}')
        self.task.log += f'{datetime.now(pytz.timezone(TIME_ZONE)).strftime("%Y-%m-%d %H:%M:%S")} - INFO - {msg}\n'
        self.task.save()

    def warning(self, msg):
        log.warning(f'{self.log_id} - {msg}')
        self.task.log += f'{datetime.now(pytz.timezone(TIME_ZONE)).strftime("%Y-%m-%d %H:%M:%S")} - WARNING - {msg}\n'
        self.task.save()

    def error(self, msg):
        log.error(f'{self.log_id} - {msg}')
        self.task.log += f'{datetime.now(pytz.timezone(TIME_ZONE)).strftime("%Y-%m-%d %H:%M:%S")} - ERROR - {msg}\n'
        self.task.save()

    def action_task(self, action, msg, reason):
        self.task.status = action
        self.task.message = msg
        self.task.fail_reason = reason
        self.task.save()
        raise UpgradeException(
            reason=reason,
            message=msg,
        )

    def skip_task(self, msg='', reason=''):
        self.action_task(TaskStatusChoices.STATUS_SKIPPED, msg, reason)

    def drop_task(self, msg='', reason=''):
        self.action_task(TaskStatusChoices.STATUS_FAILED, msg, reason)

    def check(self):
        if not hasattr(self.task.device.device_type, 'golden_image'):
            msg = f'No Golden Image for {self.task.device.device_type.model}'
            self.warning(msg)
            self.skip_task(msg, TaskFailReasonChoices.FAIL_CHECK)
        else:
            self.debug(f'Golden Image for {self.task.device.device_type.model} is {self.task.device.device_type.golden_image.sw}')

        if self.task.start_time > self.task.scheduled_time + timedelta(hours=int(self.task.mw_duration)):
            msg = 'Maintenance Window is over'
            self.warning(msg)
            self.skip_task(msg, TaskFailReasonChoices.FAIL_CHECK)
        else:
            self.debug('MW is still active')

        if self.task.task_type == TaskTypeChoices.TYPE_UPGRADE:
            q = get_queue(UPGRADE_QUEUE)
            active_jobs = q.started_job_registry.count
            non_ack = ScheduledTask.objects.filter(start_time__isnull=False, confirmed=False).count()
            if non_ack >= active_jobs + UPGRADE_THRESHOLD:
                msg = f'Reached failure threshold: Unconfirmed: {non_ack}, active: {active_jobs}, failed: {non_ack-active_jobs}, threshold: {UPGRADE_THRESHOLD}'
                self.warning(msg)
                self.skip_task(msg, TaskFailReasonChoices.FAIL_CHECK)
            else:
                self.debug(f'Unconfirmed: {non_ack}, active: {active_jobs}, failed: {non_ack - active_jobs}, threshold: {UPGRADE_THRESHOLD}')
        else:
            self.debug(f'Task type is {self.task.task_type}, check against threshold was skipped')

    def connect_cli(self, **kwargs):
        def to_telnet(cli, **kwargs):
            try:
                cli.close()
            except Exception:
                pass
            cli = False
            if self.device['port'] != 23:
                self.debug('Swiching to telnet')
                self.device['port'] = 23
                self.device['transport'] = 'telnet'
                cli = self.connect_cli(**kwargs)
            return cli

        cli = IOSXEDriver(**self.device, **kwargs)
        try:
            self.debug(f'Trying to connect via TCP/{self.device["port"]} ...')
            cli.open()
        except ScrapliAuthenticationFailed:
            self.debug(f'Incorrect username while connecting to the device via TCP/{self.device["port"]}')
            cli = to_telnet(cli, **kwargs)
        except ScrapliConnectionError:
            self.debug(f'Device closed connection on TCP/{self.device["port"]}')
            # raise
            cli = to_telnet(cli, **kwargs)
        except Exception:
            self.debug(f'Unknown error while connecting to the device via TCP/{self.device["port"]}')
            cli = to_telnet(cli, **kwargs)
        else:
            self.debug(f'Login successful while connecting to the device via TCP/{self.device["port"]}')
        return cli

    def is_alive(self):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(self.device.get('timeout_socket', 5))
                s.connect((self.device['host'], 22))
        except Exception:
            self.debug('no response on TCP/22')
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.settimeout(self.device.get('timeout_socket', 5))
                    s.connect((self.device['host'], 23))
            except Exception:
                self.debug('no response on TCP/23')
                time.sleep(2)
                return False
            else:
                self.debug('got response on TCP/23')
        else:
            self.debug('got response on TCP/22')
        time.sleep(2)
        return True

    def check_device(self):
        pid = ''
        sn = ''
        cmd = [
            'show version',
            'dir /all',
        ]

        cli = self.connect_cli()
        if not cli:
            msg = 'Can not connect to device CLI'
            self.error(msg)
            self.skip_task(msg, TaskFailReasonChoices.FAIL_CONNECT)

        output = cli.send_commands(cmd)
        cli.close()

        if output.failed:
            msg = 'Can not collect outputs from device'
            self.error(msg)
            self.skip_task(msg, TaskFailReasonChoices.FAIL_CONFIG)

        self.debug('----------vv Outputs vv----------')
        self.debug(output.result)
        self.debug('----------^^ Outputs ^^----------')

        r = re.search(r'\n\w+\s+(\S+)\s+.*\(revision\s+', output[0].result)
        if r:
            pid = r.group(1)
            # pid = re.sub('\+','plus',r.group(1))
            self.info(f'PID: {r.group(1)}')
        else:
            msg = 'Can not get device PID'
            self.error(msg)
            self.skip_task(msg, reason=TaskFailReasonChoices.FAIL_CONFIG)

        r = re.search(r'\n.*\s+board\s+ID\s+(\S+)', output[0].result)
        if r:
            sn = r.group(1)
            self.info(f'SN: {sn}')
        else:
            msg = 'Can not get device SN'
            self.error(msg)
            self.skip_task(msg, reason=TaskFailReasonChoices.FAIL_CONFIG)

        if pid.upper() != self.task.device.device_type.model.upper() or sn.lower() != self.task.device.serial.lower():
            msg = 'Device PID/SN does not match with NetBox data'
            self.error(msg)
            self.skip_task(msg, reason=TaskFailReasonChoices.FAIL_CONFIG)
        self.info(f'Device {pid}/{sn} matches with NetBox data')

        self.files = output[1].textfsm_parse_output()
        self.file_system = self.files[0]['file_system'].strip('/')
        self.target_image = self.task.device.device_type.golden_image.sw.filename
        self.target_path = self.task.device.device_type.golden_image.sw.image.path
        self.image_on_device = list(filter(lambda x: x['name'] == self.target_image, self.files))

        self.debug(f'File system: {self.file_system}')
        self.debug(f'Target Image: {self.target_image}')
        self.debug(f'Target Path: {self.target_path}')
        self.debug(f'Target Image on box: {self.image_on_device}')
        return True

    def file_upload_ftp(self):
        cmd_copy_ftp = f'copy ftp://{FTP_USERNAME}:{FTP_PASSWORD}@{FTP_SERVER}/{self.target_image} {self.file_system}/{self.target_image}'
        config = [
            'file prompt quiet',
            'line vty 0 15',
            'exec-timeout 180 0',
        ]

        config_undo = [
            'no file prompt quiet',
            'line vty 0 15',
            'exec-timeout 30 0',
        ]

        cli = self.connect_cli(timeout_ops=7200, timeout_transport=7200)
        if not cli:
            msg = 'Unable to connect to the device'
            self.error(msg)
            self.skip_task(msg, TaskFailReasonChoices.FAIL_CONNECT)

        if not len(self.image_on_device):
            self.info('No image on the device. Need to transfer')
            self.debug(
                f'Free on {self.file_system} {self.files[0]["total_free"]}, \
                Image size (+10%) {int(int(self.task.device.device_type.golden_image.sw.image.size)*1.1)}'
            )
            if int(self.files[0]['total_free']) < int(int(self.task.device.device_type.golden_image.sw.image.size)*1.1):
                try:
                    cli.close()
                except Exception:
                    pass
                msg = f'No enough space on {self.file_system}'
                self.error(msg)
                self.skip_task(msg, TaskFailReasonChoices.FAIL_UPLOAD)
            self.info('Download image from FTP...')
            output = cli.send_configs(config)
            self.debug(f'Preparing for copy:\n{output.result}')
            if output.failed:
                try:
                    cli.close()
                except Exception:
                    pass
                msg = 'Can not change configuration'
                self.error(msg)
                self.skip_task(msg, TaskFailReasonChoices.FAIL_UPLOAD)
            self.debug(f'Copy command: {cmd_copy_ftp}')
            output = cli.send_command(cmd_copy_ftp)
            self.debug(f'Copying process:\n{output.result}')
            if output.failed or not re.search(r'OK', output.result):
                try:
                    cli.close()
                except Exception:
                    pass
                msg = 'Can not download image from FTP'
                self.error(msg)
                self.skip_task(msg, TaskFailReasonChoices.FAIL_UPLOAD)

            output = cli.send_configs(config_undo)
            self.debug(f'Rollback after copy:\n{output.result}')
            if output.failed:
                try:
                    cli.close()
                except Exception:
                    pass
                msg = 'Can not do rollback configuration'
                self.error(msg)
                self.skip_task(msg, TaskFailReasonChoices.FAIL_UPLOAD)
        else:
            self.info(f'Image {self.target_image} already exists')
        self.info('MD5 verification ...')

        md5 = cli.send_command(f'verify /md5 {self.file_system}/{self.target_image} {self.task.device.device_type.golden_image.sw.md5sum}')
        self.debug(f'MD5 verication result:\n{md5.result[-200:]}')
        if md5.failed:
            try:
                cli.close()
            except Exception:
                pass
            msg = 'Can not check MD5'
            self.error(msg)
            self.skip_task(msg, TaskFailReasonChoices.FAIL_CHECK)
        if re.search(r'Verified', md5.result):
            self.info('MD5 was verified')
        else:
            try:
                cli.close()
            except Exception:
                pass
            msg = 'Wrong M5'
            self.error(msg)
            self.skip_task(msg, TaskFailReasonChoices.FAIL_CHECK)
        try:
            cli.close()
        except Exception:
            pass
        self.info('File was uploaded and verified')
        return True

    def device_reload(self):
        cmd = [
            'show run | i boot system',
            'show version',
        ]
        cli = self.connect_cli()
        if not cli:
            msg = 'Unable to connect to the device'
            self.error(msg)
            self.skip_task(msg, TaskFailReasonChoices.FAIL_CONNECT)

        output = cli.send_commands(cmd)
        self.debug(f'Collected outputs:------vvvvv\n{output.result}\n-----^^^^^')
        if output.failed:
            try:
                cli.close()
            except Exception:
                pass
            msg = 'Can not collect outputs for upgrade'
            self.error(msg)
            self.skip_task(msg, TaskFailReasonChoices.FAIL_UPGRADE)

        parsed = output[1].textfsm_parse_output()
        sw_current = parsed[0].get('version', 'N/A')
        sw_target = self.task.device.device_type.golden_image.sw.version
        self.debug(f'Current version is {sw_current}')
        if sw_current.upper() == sw_target.upper():
            msg = f'Current version {sw_current} matches with target {sw_target}'
            self.warning(msg)
            self.info('Update custom field')
            self.task.device.custom_field_data[CF_NAME_SW_VERSION] = sw_current
            self.task.device.save()
            self.skip_task(msg, TaskFailReasonChoices.FAIL_UPGRADE)

        if not len(self.image_on_device):
            msg = 'No target image on the box'
            self.error(msg)
            self.skip_task(msg, TaskFailReasonChoices.FAIL_UPGRADE)
        self.info('Image exists on the box')

        cli.timeout_ops = 600
        self.info('MD5 verification ...')
        md5 = cli.send_command(f'verify /md5 {self.file_system}/{self.target_image} {self.task.device.device_type.golden_image.sw.md5sum}')
        self.debug(f'MD5 verication result:\n{md5.result[-200:]}')
        if md5.failed:
            try:
                cli.close()
            except Exception:
                pass
            msg = 'Can not check MD5'
            self.error(msg)
            self.skip_task(msg, TaskFailReasonChoices.FAIL_CHECK)
        if re.search(r'Verified', md5.result):
            self.info('MD5 was verified')
        else:
            try:
                cli.close()
            except Exception:
                pass
            msg = 'Wrong M5'
            self.error(msg)
            self.skip_task(msg, TaskFailReasonChoices.FAIL_CHECK)
        cli.timeout_ops = 10

        self.info('Preparing boot system config')
        new_boot_lines = []
        old_boot_lines = output[0].result.splitlines()
        self.debug(f'Orginal boot lines:\n{old_boot_lines}')
        for line in old_boot_lines:
            new_boot_lines.append(f'no {line}')
        new_boot_lines.append(f'boot system {self.file_system}/{self.target_image}')
        if len(old_boot_lines):
            new_boot_lines.append(old_boot_lines[0])
        self.debug(f'New boot lines:\n{new_boot_lines}')
        output = cli.send_configs(new_boot_lines)
        self.debug(f'Changnig Boot vars:\n{output.result}')
        if output.failed:
            msg = 'Unable to change bootvar'
            self.error(msg)
            self.drop_task(msg, TaskFailReasonChoices.FAIL_UPGRADE)
        else:
            self.info('Bootvar was changed')

        self.info('Write memory before reload')
        try:
            output = cli.send_command('write memory')
        except (ScrapliTimeout, ScrapliConnectionError):
            self.info('Interactive prompt was detected')
            time.sleep(2)
            cli.open()
            try:
                output_tmp = cli.send_interactive([
                    ('write', '[confirm]', False),
                    ('\n', '#', False),
                ])
            except (ScrapliTimeout, ScrapliConnectionError):
                msg = 'Unable to write memory: ScrapliTimeout'
                self.error(msg)
                self.drop_task(msg, TaskFailReasonChoices.FAIL_UPGRADE)
            else:
                output = output_tmp
        if re.search(r'\[OK\]', output.result):
            self.info('Config was saved')
        else:
            msg = 'Can not save config'
            self.error(msg)
            self.drop_task(msg, TaskFailReasonChoices.FAIL_UPGRADE)

        self.info('Reloading the box')
        try:
            output = cli.send_interactive([
                ('reload in 1', '[confirm]', False),
                ('\n', '#', False),
            ])
        except ScrapliTimeout:
            msg = 'Unable to reload: ScrapliTimeout'
            self.error(msg)
            self.drop_task(msg, TaskFailReasonChoices.FAIL_UPGRADE)
        else:
            self.info('Reload was requested')
        try:
            cli.close()
        except Exception:
            pass
        return True

    def post_check(self):
        cmd = [
            'show version',
        ]

        cli = self.connect_cli()
        if not cli:
            msg = 'Unable to connect to the device'
            self.error(msg)
            self.drop_task(msg, TaskFailReasonChoices.FAIL_CONNECT)
        output = cli.send_commands(cmd)
        self.debug(f'Commands output\n{output.result}')
        if output.failed:
            msg = 'Can not collect outputs for post-chech'
            self.error(msg)
            self.drop_task(msg, TaskFailReasonChoices.FAIL_UPGRADE)

        parsed = output[0].textfsm_parse_output()
        self.info(f'New version is {parsed[0].get("version", "N/A")}')

        self.info('Write memory after reload')
        try:
            output = cli.send_command('write memory')
        except (ScrapliTimeout, ScrapliConnectionError):
            self.info('Interactive prompt was detected')
            time.sleep(2)
            cli.open()
            try:
                output_tmp = cli.send_interactive([
                    ('write', '[confirm]', False),
                    ('\n', '#', False),
                ])
            except (ScrapliTimeout, ScrapliConnectionError):
                msg = 'Unable to write memory: ScrapliTimeout'
                self.error(msg)
                self.drop_task(msg, TaskFailReasonChoices.FAIL_UPGRADE)
            else:
                output = output_tmp
        if re.search(r'\[OK\]', output.result):
            self.info('Config was saved')
        else:
            msg = 'Can not save config'
            self.error(msg)
            self.drop_task(msg, TaskFailReasonChoices.FAIL_UPGRADE)
        cli.close()

        self.info('Update custom field')
        self.task.device.custom_field_data[CF_NAME_SW_VERSION] = parsed[0].get('version', 'N/A')
        self.task.device.save()
        self.info('Post-checks have been done')
        return True

    def execute_task(self):
        self.info(f'New Job {self.task.job_id} was started. Type {self.task.task_type}')
        self.info('Initial task checking...')
        self.check()
        self.info('Initial task check has been completed')

        self.info('Checking if device alive...')
        if not self.is_alive():
            msg = f'Device {self.task.device.name}:{self.task.device.primary_ip.address.ip} is not reachable'
            self.warning(msg)
            self.skip_task(msg, TaskFailReasonChoices.FAIL_CONNECT)
        else:
            msg = f'Device {self.task.device.name}:{self.task.device.primary_ip.address.ip} is reachable'
            self.info(msg)

        self.info('Device valiation...')
        self.check_device()
        self.info('Device has been validated')

        if self.task.task_type == TaskTypeChoices.TYPE_UPLOAD:
            self.info('Uploadng image on the box...')
            self.file_upload_ftp()
        elif self.task.task_type == TaskTypeChoices.TYPE_UPGRADE:
            self.info('Reloading the box...')
            self.device_reload()
            hold_timer = 240
            self.info(f'Hold for {hold_timer} seconds')
            time.sleep(hold_timer)
            for try_number in range(1, UPGRADE_MAX_ATTEMPTS_AFTER_RELOAD + 1):
                self.info(f'Connecting after reload {try_number}/{UPGRADE_MAX_ATTEMPTS_AFTER_RELOAD}...')
                if self.is_alive():
                    self.info('Device became online')
                    time.sleep(10)
                    break
                else:
                    self.info(f'Device is not online, next try in {UPGRADE_SECONDS_BETWEEN_ATTEMPTS} seconds')
                time.sleep(UPGRADE_SECONDS_BETWEEN_ATTEMPTS)
            if not self.is_alive():
                msg = 'Device was lost after reload'
                self.error(msg)
                self.drop_task(msg, TaskFailReasonChoices.FAIL_UPGRADE)
            else:
                self.info('Checks after reload')
                self.post_check()

        return True
