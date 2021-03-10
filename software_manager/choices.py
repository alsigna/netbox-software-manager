from utilities.choices import ChoiceSet


class TaskTypeChoices(ChoiceSet):
    TYPE_UPLOAD = 'upload'
    TYPE_UPGRADE = 'upgrade'

    CHOICES = (
        (TYPE_UPLOAD, 'upload'),
        (TYPE_UPGRADE, 'upgrade'),
    )


class TaskStatusChoices(ChoiceSet):
    STATUS_UNKNOWN = 'unknown'
    STATUS_SCHEDULED = 'scheduled'
    STATUS_FAILED = 'failed'
    STATUS_RUNNING = 'running'
    STATUS_SUCCEEDED = 'succeeded'
    STATUS_SKIPPED = 'skipped'

    CHOICES = (
        (STATUS_UNKNOWN, 'unknown'),
        (STATUS_SCHEDULED, 'scheduled'),
        (STATUS_FAILED, 'failed'),
        (STATUS_RUNNING, 'running'),
        (STATUS_SUCCEEDED, 'succeeded'),
        (STATUS_SKIPPED, 'skipped'),
    )


class TaskFailReasonChoices(ChoiceSet):
    FAIL_UNKNOWN = 'fail-unknown'
    FAIL_CHECK = 'fail-check'
    FAIL_LOGIN = 'fail-login'
    FAIL_CONFIG = 'fail-config'
    FAIL_CONNECT = 'fail-connect'
    FAIL_GENERAL = 'fail-general'
    FAIL_ADD = 'fail-add'
    FAIL_UPGRADE = 'fail-upgrade'
    FAIL_UPLOAD = 'fail-upload'

    CHOICES = (
        (FAIL_UNKNOWN, 'fail-unknown'),
        (FAIL_CHECK, 'fail-check'),
        (FAIL_LOGIN, 'fail-login'),
        (FAIL_CONFIG, 'fail-config'),
        (FAIL_CONNECT, 'fail-connect'),
        (FAIL_GENERAL, 'fail-general'),
        (FAIL_ADD, 'fail-add'),
        (FAIL_UPGRADE, 'fail-upgrade'),
        (FAIL_UPLOAD, 'fail-upload'),
    )
