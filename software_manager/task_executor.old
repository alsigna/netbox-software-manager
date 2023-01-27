import re
import socket
import time
from datetime import timedelta
from functools import wraps
from pathlib import Path
from typing import Callable

from django.conf import settings
from django_rq import get_queue
from scrapli.driver.core import IOSXEDriver
from scrapli.exceptions import ScrapliAuthenticationFailed, ScrapliConnectionError, ScrapliTimeout
from scrapli.response import MultiResponse, Response

from .choices import TaskFailReasonChoices, TaskStatusChoices, TaskTransferMethod, TaskTypeChoices
from .logger import TaskLoggerMixIn
from .models import ScheduledTask
from .task_exceptions import TaskException

PLUGIN_SETTINGS = settings.PLUGINS_CONFIG.get("software_manager", dict())
DEVICE_USERNAME = PLUGIN_SETTINGS.get("DEVICE_USERNAME", "")
DEVICE_PASSWORD = PLUGIN_SETTINGS.get("DEVICE_PASSWORD", "")
UPGRADE_QUEUE = PLUGIN_SETTINGS.get("UPGRADE_QUEUE", "")
UPGRADE_THRESHOLD = PLUGIN_SETTINGS.get("UPGRADE_THRESHOLD", 2)
FTP_USERNAME = PLUGIN_SETTINGS.get("FTP_USERNAME", "")
FTP_PASSWORD = PLUGIN_SETTINGS.get("FTP_PASSWORD", "")
FTP_SERVER = PLUGIN_SETTINGS.get("FTP_SERVER", "")
HTTP_SERVER = PLUGIN_SETTINGS.get("HTTP_SERVER", "")
CF_NAME_SW_VERSION = PLUGIN_SETTINGS.get("CF_NAME_SW_VERSION", "")
UPGRADE_MAX_ATTEMPTS_AFTER_RELOAD = PLUGIN_SETTINGS.get("UPGRADE_MAX_ATTEMPTS_AFTER_RELOAD", 10)
UPGRADE_SECONDS_BETWEEN_ATTEMPTS = PLUGIN_SETTINGS.get("UPGRADE_SECONDS_BETWEEN_ATTEMPTS", 60)


class TaskExecutor(TaskLoggerMixIn):
    def __init__(self, task: ScheduledTask) -> None:
        super().__init__(task)
        self.task = task
        self.cli = None
        self.scrapli = {
            "auth_username": DEVICE_USERNAME,
            "auth_password": DEVICE_PASSWORD,
            "auth_strict_key": False,
            "port": 22,
            "timeout_socket": 5,
            "transport": "paramiko",
            "transport_options": {
                "open_cmd": [
                    "-o",
                    "KexAlgorithms=+diffie-hellman-group-exchange-sha1",
                ],
            },
        }
        if self.task.device is not None and self.task.device.primary_ip is not None:
            self.scrapli["host"] = str(self.task.device.primary_ip.address.ip)
        else:
            self.scrapli["host"] = None

        self.file_system = None
        self.target_image = None
        self.image_on_device = None
        self.total_free = 0

    def _action_task(self, status: str, msg: str, reason: str) -> None:
        self.task.status = status
        self.task.message = msg
        self.task.fail_reason = reason
        self.task.save()
        raise TaskException(
            reason=reason,
            message=msg,
        )

    def skip_task(self, msg: str = "", reason: str = "") -> None:
        self._close_cli()
        self._action_task(TaskStatusChoices.STATUS_SKIPPED, msg, reason)

    def drop_task(self, msg: str = "", reason: str = "") -> None:
        self._close_cli()
        self._action_task(TaskStatusChoices.STATUS_FAILED, msg, reason)

    def _check_device_exists(self) -> None:
        if self.task.device is None:
            msg = "_check_device_exists - FAIL: No device is assigned to task"
            self.warning(msg)
            self.skip_task(msg, TaskFailReasonChoices.FAIL_CHECK)
        else:
            self.debug(f"_check_device_exists - OK: device='{self.task.device}'")

    def _check_primary_ip_exists(self) -> None:
        if self.task.device is None:
            return
        if self.task.device.primary_ip is None:
            msg = "_check_primary_ip_exists - FAIL: No primary (mgmt) address"
            self.warning(msg)
            self.skip_task(msg, TaskFailReasonChoices.FAIL_CHECK)
        else:
            ip = str(self.task.device.primary_ip.address.ip)
            self.debug(f"_check_primary_ip_exists - OK: {ip=}")

    def _check_golden_image_is_set(self) -> None:
        if self.task.device is None:
            return
        device_type = self.task.device.device_type
        if not hasattr(device_type, "golden_image"):
            msg = f"_check_golden_image_is_set - FAIL: No Golden Image for '{device_type.model}'"
            self.warning(msg)
            self.skip_task(msg, TaskFailReasonChoices.FAIL_CHECK)
        self.debug(
            f"_check_golden_image_is_set - OK: Golden Image for '{device_type.model}' is '{device_type.golden_image.sw}'"
        )

    def _check_software_image_file_exists(self) -> None:
        if self.task.device is None:
            return
        sw = self.task.device.device_type.golden_image.sw

        if not sw.image_exists:
            msg = "_check_software_image_file_exists - OK: SoftwareImage was created without file, no need to check"
            self.warning(msg)
            return

        if not Path(settings.MEDIA_ROOT, sw.image.name).is_file():
            msg = "_check_software_image_file_exists - FAIL: Image file does not exist in NetBox media directory"
            self.warning(msg)
            self.skip_task(msg, TaskFailReasonChoices.FAIL_CHECK)
        self.debug("_check_software_image_file_exists - OK: Image file exists in NetBox media directory")

    def _check_mw_is_active(self) -> None:
        if not all([self.task.scheduled_time, self.task.mw_duration, self.task.start_time]):
            msg = "_check_mw_is_active - FAIL: issue with datetimes"
            self.warning(msg)
            self.skip_task(msg, TaskFailReasonChoices.FAIL_CHECK)
        if self.task.start_time > self.task.scheduled_time + timedelta(hours=int(self.task.mw_duration)):  # type: ignore
            msg = "_check_mw_is_active - FAIL: Maintenance Window is over"
            self.warning(msg)
            self.skip_task(msg, TaskFailReasonChoices.FAIL_CHECK)
        self.debug("_check_mw_is_active - OK: Maintenance Window is still active")

    def _check_failure_theshold(self) -> None:
        if UPGRADE_THRESHOLD is None:
            msg = "_check_failure_theshold - FAIL: UPGRADE_THRESHOLD is not set"
            self.warning(msg)
            self.skip_task(msg, TaskFailReasonChoices.FAIL_CHECK)
        if self.task.task_type == TaskTypeChoices.TYPE_UPGRADE:
            queue = get_queue(UPGRADE_QUEUE)
            active_jobs = queue.started_job_registry.count
            non_ack = ScheduledTask.objects.filter(start_time__isnull=False, confirmed=False).count()
            if non_ack >= active_jobs + UPGRADE_THRESHOLD:
                msg = (
                    f"_check_failure_theshold - FAIL: Reached failure threshold, Unconfirmed: {non_ack}, "
                    f"Active: {active_jobs}, Failed: {non_ack-active_jobs}, Threshold: {UPGRADE_THRESHOLD}"
                )
                self.warning(msg)
                self.skip_task(msg, TaskFailReasonChoices.FAIL_CHECK)
            else:
                msg = (
                    f"_check_failure_theshold - OK: Unconfirmed: {non_ack}, Active: {active_jobs}, "
                    f"Failed: {non_ack - active_jobs}, Threshold: {UPGRADE_THRESHOLD}"
                )
                self.debug(msg)
        else:
            self.debug(f"_check_failure_theshold - OK: Task type is '{self.task.task_type}', no need to check")

    def _check_device_is_alive(self) -> None:
        if self.task.device is None or self.task.device.primary_ip is None:
            return
        if (port := self._is_alive()) is not None:
            msg = f"_check_device_is_alive - OK: device is reachable via TCP/{port}"
            self.debug(msg)
        else:
            msg = "_check_device_is_alive - FAIL: device is not reachable"
            self.warning(msg)
            self.skip_task(msg, TaskFailReasonChoices.FAIL_CHECK)

    def _is_port_open(self, port: int) -> bool:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(self.scrapli.get("timeout_socket", 5))
                s.connect((self.scrapli["host"], port))
        except Exception:
            time.sleep(2)
            raise
        return True

    def _is_alive(self, ports: tuple = (22, 23)) -> int | None:
        for port in ports:
            try:
                self._is_port_open(port)
            except Exception:
                pass
            else:
                return port

    def _get_cli(self, **kwargs) -> None | IOSXEDriver:
        def fallback_to_telnet(cli, **kwargs) -> None | IOSXEDriver:
            try:
                cli.close()
            except Exception:
                pass
            cli = None
            if self.scrapli["port"] != 23:
                self.debug("Fallback to telnet")
                self.scrapli["port"] = 23
                self.scrapli["transport"] = "telnet"
                cli = self._get_cli(**kwargs)
            return cli

        cli = IOSXEDriver(**self.scrapli, **kwargs)
        try:
            self.debug(f'Trying to connect via TCP/{self.scrapli["port"]} ...')
            cli.open()
        except ScrapliAuthenticationFailed:
            self.debug(f'Incorrect username while connecting to the device via TCP/{self.scrapli["port"]}')
            cli = fallback_to_telnet(cli, **kwargs)
        except ScrapliConnectionError:
            self.debug(f'Device closed connection on TCP/{self.scrapli["port"]}')
            cli = fallback_to_telnet(cli, **kwargs)
        except Exception:
            self.debug(f'Unknown error while connecting to the device via TCP/{self.scrapli["port"]}')
            cli = fallback_to_telnet(cli, **kwargs)
        else:
            self.debug(f'Login successful while connecting to the device via TCP/{self.scrapli["port"]}')
        return cli

    @staticmethod
    def _check_cli_is_active(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            if self.cli is None:
                self.cli = self._get_cli()

            if self.cli is not None:
                try:
                    _ = self.cli.get_prompt()
                except:
                    self._close_cli()
                    self.cli = self._get_cli()

            if self.cli is None:
                msg = "_check_cli_is_active - FAIL: Cannot establish cli session"
                self.warning(msg)
                self.skip_task(msg, TaskFailReasonChoices.FAIL_CONNECT)

            return func(self, *args, **kwargs)

        return wrapper

    def _backup_cli_args(self, **kwargs) -> dict:
        backup = {}
        if self.cli is None:
            return backup
        for arg in kwargs:
            backup[arg] = getattr(self.cli, arg, None)
        return backup

    def _set_cli_args(self, backup: dict) -> None:
        if self.cli is None:
            return
        for arg, value in backup.items():
            setattr(self.cli, arg, value)

    def _close_cli(self) -> None:
        if self.cli is not None:
            try:
                self.cli.close()
            except:
                pass

    @_check_cli_is_active
    def _send_commands(self, commands: list[str], **kwargs) -> None | MultiResponse:
        if self.cli is None:
            return
        cli_backup = self._backup_cli_args(**kwargs)
        self._set_cli_args(kwargs)
        try:
            outputs = self.cli.send_commands(commands)
        except:
            raise
        else:
            return outputs
        finally:
            self._set_cli_args(cli_backup)

    @_check_cli_is_active
    def _send_configs(self, configs: list[str], **kwargs) -> None | MultiResponse:
        if self.cli is None:
            return
        cli_backup = self._backup_cli_args(**kwargs)
        self._set_cli_args(kwargs)
        try:
            outputs = self.cli.send_configs(configs)
        except:
            raise
        else:
            return outputs
        finally:
            self._set_cli_args(cli_backup)

    def _parse_pid(self, output: Response) -> str:
        if output.failed:
            msg = f"Cannot get '{output.channel_input}' output"
            self.error(msg)
            self.skip_task(msg, reason=TaskFailReasonChoices.FAIL_CONFIG)

        if match := re.search(r"\n\w+\s+(\S+)\s+.*\(revision\s+", output.result):
            pid = match.group(1)
            self.info(f"PID: '{pid}'")
            return pid
        else:
            msg = "Cannot get device PID"
            self.error(msg)
            self.skip_task(msg, reason=TaskFailReasonChoices.FAIL_CONFIG)
        return ""

    def _parse_sn(self, output: Response) -> str:
        if output.failed:
            msg = f"Cannot get '{output.channel_input}' output"
            self.error(msg)
            self.skip_task(msg, reason=TaskFailReasonChoices.FAIL_CONFIG)

        if match := re.search(r"\n.*\s+board\s+ID\s+(\S+)", output.result):
            sn = match.group(1)
            self.info(f"SN: '{sn}'")
            return sn
        else:
            msg = "Can not get device SN"
            self.error(msg)
            self.skip_task(msg, reason=TaskFailReasonChoices.FAIL_CONFIG)
        return ""

    def _validate_pid_sn(self, show_version_output: Response) -> None:
        if self.task.device is None:
            return

        pid = self._parse_pid(show_version_output)
        sn = self._parse_sn(show_version_output)

        if pid.lower() != self.task.device.device_type.model.lower() or sn.lower() != self.task.device.serial.lower():
            msg = "Device PID/SN does not match with NetBox data"
            self.error(msg)
            self.skip_task(msg, reason=TaskFailReasonChoices.FAIL_CONFIG)
        self.info(f"Device '{pid}/{sn}' matches with NetBox data")

    def _validate_image_file(self, dir_all_output: Response) -> None:
        if self.task.device is None:
            return
        if not self.task.device.device_type.golden_image.sw.image_exists:
            self.debug(f"SoftwareImage was created without file, no need to validate against device files")
            return

        device_files: list[dict] = dir_all_output.textfsm_parse_output()  # type: ignore
        if len(device_files) == 0:
            msg = "No any files on device flash"
            self.warning(msg)
            self.skip_task(msg, TaskFailReasonChoices.FAIL_CONFIG)

        self.file_system = device_files[0]["file_system"].strip("/")
        self.total_free = int(device_files[0]["total_free"])
        self.target_image = self.task.device.device_type.golden_image.sw.filename
        target_path = self.task.device.device_type.golden_image.sw.image.path
        self.image_on_device = list(filter(lambda x: x["name"] == self.target_image, device_files))

        self.debug(f"Filesystem: {self.file_system}")
        self.debug(f"Target Image: {self.target_image}")
        self.debug(f"Target Path: {target_path}")
        self.debug(f"Target Image on box: {self.image_on_device}")

    def _validate_device(self) -> None:
        self.info("Device valiation...")

        commands = ["show version", "dir /all"]
        outputs = self._send_commands(commands)
        self.debug("----------vv Outputs vv----------")
        for output in outputs:
            self.debug("\n" + output.result)
        self.debug("----------^^ Outputs ^^----------")
        self._validate_pid_sn(outputs[0])
        self._validate_image_file(outputs[1])

        self.info("Device has been validated")

    def _initial_check(self) -> None:
        self.info("Initial checking...")
        self._check_device_exists()
        self._check_primary_ip_exists()
        self._check_golden_image_is_set()
        self._check_software_image_file_exists()
        self._check_mw_is_active()
        self._check_failure_theshold()
        self._check_device_is_alive()
        self.info("Initial checks have been completed")

    def _file_upload(self) -> None:
        self.info("Uploading image to the box...")
        cmd_copy = ""
        if self.task.transfer_method == TaskTransferMethod.METHOD_FTP:
            cmd_copy = f"copy ftp://{FTP_USERNAME}:{FTP_PASSWORD}@{FTP_SERVER}/{self.target_image} {self.file_system}/{self.target_image}"
        elif self.task.transfer_method == TaskTransferMethod.METHOD_HTTP:
            cmd_copy = f"copy {HTTP_SERVER}{self.target_image} {self.file_system}/{self.target_image}"
        else:
            msg = "Unknown transfer method"
            self.error(msg)
            self.skip_task(msg, reason=TaskFailReasonChoices.FAIL_UPLOAD)

        configs = [
            "file prompt quiet",
            "line vty 0 15",
            "exec-timeout 180 0",
        ]
        configs_undo = [
            "no file prompt quiet",
            "line vty 0 15",
            "exec-timeout 30 0",
        ]
        outputs = self._send_configs(configs)
        self.debug(f"Preparing for copy:\n{outputs.result}")
        if outputs.failed:
            self._close_cli()
            msg = "Can not change configuration"
            self.error(msg)
            self.skip_task(msg, TaskFailReasonChoices.FAIL_UPLOAD)

        self.debug(f"Copy command: {cmd_copy}")
        self.info(f"Copy in progress...")

        outputs = self._send_commands(
            [cmd_copy],
            timeout_ops=7200,
            timeout_transport=7200,
        )
        self.debug(f"Copy logs:\n{outputs.result}")
        if outputs.failed or not (re.search(r"OK", outputs.result) or re.search(r"bytes copied in", outputs.result)):
            self._close_cli()
            msg = "Can not download image from server"
            self.error(msg)
            self.skip_task(msg, TaskFailReasonChoices.FAIL_UPLOAD)

        outputs = self._send_configs(configs_undo)
        self.debug(f"Rollback after copy:\n{outputs.result}")
        if outputs.failed:
            self._close_cli()
            msg = "Can not do rollback configuration"
            self.error(msg)
            self.skip_task(msg, TaskFailReasonChoices.FAIL_UPLOAD)

    def _check_md5(self, filename: str, expected_md5: str) -> None:
        outputs = self._send_commands(
            [f"verify /md5 {filename} {expected_md5}"],
            timeout_ops=1800,
            timeout_transport=1800,
        )

        self.debug(f"MD5 verication result:\n{outputs.result[-150:]}")
        if outputs.failed:
            self._close_cli()
            msg = "Can not check MD5"
            self.error(msg)
            self.skip_task(msg, TaskFailReasonChoices.FAIL_CHECK)

        if re.search(r"Verified", outputs.result):
            self.info("MD5 was verified")
        else:
            self._close_cli()
            msg = "Wrong M5"
            self.error(msg)
            self.skip_task(msg, TaskFailReasonChoices.FAIL_CHECK)

    def _upload(self) -> None:
        if self.task.device is None:
            return
        if not self.task.device.device_type.golden_image.sw.image_exists:
            msg = f"SoftwareImage was created without file, upload is not applicable"
            self.warning(msg)
            self.skip_task(msg, TaskFailReasonChoices.FAIL_UPLOAD)
        if not all([self.target_image, self.file_system, self.total_free]):
            msg = "Was not able to parse files on device flash."
            self.warning(msg)
            self.skip_task(msg, TaskFailReasonChoices.FAIL_UPLOAD)

        if self.image_on_device is not None and len(self.image_on_device) == 0:
            self.info("No image on the device. Need to transfer")
            image_size = int(self.task.device.device_type.golden_image.sw.image.size) * 1.1
            self.debug(f"Free on {self.file_system} - {self.total_free}, Image size (+10%) - {int(image_size)}")

            if int(self.total_free) < int(image_size):
                self._close_cli()
                msg = f"No enough space on {self.file_system}"
                self.error(msg)
                self.skip_task(msg, TaskFailReasonChoices.FAIL_UPLOAD)
            else:
                self.debug("Enough space for uploading, contunue proccessing")
            self._file_upload()
        else:
            self.info(f"Image {self.target_image} already exists")

        self.info("MD5 verification...")
        self._check_md5(
            filename=f"{self.file_system}/{self.target_image}",
            expected_md5=self.task.device.device_type.golden_image.sw.md5sum,
        )
        self.info("File was uploaded and verified")
        self._close_cli()

    def _compare_sw(self, show_version_output: Response, should_match: bool) -> None:
        if self.task.device is None:
            return
        show_ver_parsed = show_version_output.textfsm_parse_output()
        sw_current = show_ver_parsed[0].get("version", "N/A")  # type: ignore
        sw_target = self.task.device.device_type.golden_image.sw.version
        self.debug(f"Current version is '{sw_current}'")
        self.debug(f"Target version is '{sw_target}'")
        if self.task.device.custom_field_data[CF_NAME_SW_VERSION] != sw_current:
            self.info("Updating custom field")
            self.task.device.custom_field_data[CF_NAME_SW_VERSION] = sw_current
            self.task.device.save()
        if should_match and sw_current.lower() != sw_target.lower():
            msg = f"Current version '{sw_current}' does not match with target '{sw_target}' after upgrade"
            self.error(msg)
            self.drop_task(msg, TaskFailReasonChoices.FAIL_UPGRADE)
        elif not should_match and sw_current.lower() == sw_target.lower():
            msg = f"Current version '{sw_current}' matches with target '{sw_target}'"
            self.warning(msg)
            self.skip_task(msg, TaskFailReasonChoices.FAIL_UPGRADE)

    def _change_bootvar(self, show_boot_output: Response) -> None:
        self.info("Preparing boot system config")
        new_boot_lines = []
        old_boot_lines = show_boot_output.result.splitlines()
        self.debug(f"Orginal boot lines:\n{old_boot_lines}")
        for line in old_boot_lines:
            new_boot_lines.append(f"no {line}")
        new_boot_lines.append(f"boot system {self.file_system}/{self.target_image}")
        if len(old_boot_lines) != 0:
            new_boot_lines.append(old_boot_lines[0])
        self.debug(f"New boot lines:\n{new_boot_lines}")

        output = self._send_configs(new_boot_lines)
        self.debug(f"Changnig Boot vars:\n{output.result}")
        if output.failed:
            msg = "Unable to change bootvar"
            self.error(msg)
            self.drop_task(msg, TaskFailReasonChoices.FAIL_UPGRADE)
        else:
            self.info("Bootvar was changed")

    @_check_cli_is_active
    def _write_memory(self) -> None:
        self.info("Write memory")
        if self.cli is None:
            return

        try:
            output = self.cli.send_command(command="write memory", timeout_ops=60)
        except (ScrapliTimeout, ScrapliConnectionError):
            self.info("Trying interactive prompt")
            time.sleep(2)
            self._close_cli()
            self.cli = self._get_cli()
            try:
                output = self.cli.send_interactive(  # type: ignore
                    [
                        ("write memory", "]", False),
                        ("\n", "#", False),
                        ("\n", "#", False),
                    ],
                    timeout_ops=60,
                )
            except (ScrapliTimeout, ScrapliConnectionError):
                msg = "Unable to save config: ScrapliTimeout"
                self.error(msg)
                self.drop_task(msg, TaskFailReasonChoices.FAIL_UPGRADE)
            except Exception as exc:
                msg = f"Unable to save config, unknown exception: {str(exc)}"
                self.error(msg)
                self.drop_task(msg, TaskFailReasonChoices.FAIL_UPGRADE)
        except Exception as exc:
            msg = f"Unable to save config, unknown exception: {str(exc)}"
            self.error(msg)
            self.drop_task(msg, TaskFailReasonChoices.FAIL_UPGRADE)

        self.debug("----------vv Outputs vv----------")
        self.debug("\n" + output.result)  # type: ignore
        self.debug("----------^^ Outputs ^^----------")

        if re.search(r"\[OK\]", output.result):  # type: ignore
            self.info("Config was saved")
        else:
            msg = "Can not save config"
            self.error(msg)
            self.drop_task(msg, TaskFailReasonChoices.FAIL_UPGRADE)

    @_check_cli_is_active
    def _reload_in(self) -> None:
        self.info("Reloading the box")
        if self.cli is None:
            return

        try:
            output = self.cli.send_interactive(
                [
                    ("reload in 1", "[confirm]", False),
                    ("\n", "#", False),
                    ("\n", "#", False),
                ],
                timeout_ops=30,
            )
        except Exception as exc:
            msg = f"Unable to reload, exception: {str(exc)}"
            self.error(msg)
            self.drop_task(msg, TaskFailReasonChoices.FAIL_UPGRADE)
        else:
            self.info("Reload was requested")
            self.debug("----------vv Outputs vv----------")
            self.debug("\n" + output.result)  # type: ignore
            self.debug("----------^^ Outputs ^^----------")

    def _wait_for_device_up(self) -> None:
        hold_timer = 30
        self.info(f"Hold for {hold_timer} seconds")
        time.sleep(hold_timer)
        for try_number in range(1, UPGRADE_MAX_ATTEMPTS_AFTER_RELOAD + 1):
            self.info(f"Connecting after reload {try_number}/{UPGRADE_MAX_ATTEMPTS_AFTER_RELOAD}...")
            if not self._is_alive():
                self.info(f"Device is not online, next try in {UPGRADE_SECONDS_BETWEEN_ATTEMPTS} seconds")
                time.sleep(UPGRADE_SECONDS_BETWEEN_ATTEMPTS)
            else:
                self.info("Device became online")
                time.sleep(10)
                return
        if not self._is_alive():
            msg = "Device was lost after reload"
            self.error(msg)
            self.drop_task(msg, TaskFailReasonChoices.FAIL_UPGRADE)

    def _post_checking(self) -> None:
        self.info("Checking after reload")

        commands = ["show version"]
        outputs = self._send_commands(commands)
        if outputs[0].failed:
            msg = "Can not collect outputs for post-chech"
            self.error(msg)
            self.drop_task(msg, TaskFailReasonChoices.FAIL_UPGRADE)
        self.debug("----------vv Outputs vv----------")
        for output in outputs:
            self.debug("\n" + output.result)
        self.debug("----------^^ Outputs ^^----------")

        self._write_memory()
        self._compare_sw(outputs[0], should_match=True)
        self.info("Post-checks have been done")

    def _upgrade(self) -> None:
        if self.task.device is None:
            return
        commands = [
            "show run | i boot system",
            "show version",
        ]
        outputs = self._send_commands(commands)

        self.debug("----------vv Outputs vv----------")
        for output in outputs:
            self.debug("\n" + output.result)
        self.debug("----------^^ Outputs ^^----------")

        if outputs.failed:
            self._close_cli()
            msg = "Can not collect outputs for upgrade"
            self.error(msg)
            self.skip_task(msg, TaskFailReasonChoices.FAIL_UPGRADE)

        self._compare_sw(outputs[1], should_match=False)

        if not self.task.device.device_type.golden_image.sw.image_exists:
            msg = f"SoftwareImage was created without file, upgrade is not applicable"
            self.warning(msg)
            self.skip_task(msg, TaskFailReasonChoices.FAIL_UPGRADE)

        if self.image_on_device is None or len(self.image_on_device) == 0:
            msg = "No target image on the box"
            self.error(msg)
            self.skip_task(msg, TaskFailReasonChoices.FAIL_UPGRADE)
        else:
            self.info("Image exists on the box")

        self._check_md5(
            filename=f"{self.file_system}/{self.target_image}",
            expected_md5=self.task.device.device_type.golden_image.sw.md5sum,
        )
        self._check_failure_theshold()
        self._change_bootvar(outputs[0])
        self._write_memory()
        self._reload_in()
        self._close_cli()
        self._wait_for_device_up()
        self._post_checking()

    def execute_task(self) -> bool:
        self.info(f"New Job {self.task.job_id} was started. Type {self.task.task_type}")
        self._initial_check()
        self._validate_device()

        if self.task.task_type == TaskTypeChoices.TYPE_UPLOAD:
            self.info("Upload task")
            self._upload()
        elif self.task.task_type == TaskTypeChoices.TYPE_UPGRADE:
            self.info("Upgrade task")
            self._upgrade()

        return True
