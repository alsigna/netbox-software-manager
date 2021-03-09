#!/bin/bash
/opt/netbox/venv/bin/python /opt/netbox/netbox/manage.py rqworker software_manager &
/opt/netbox/venv/bin/python /opt/netbox/netbox/manage.py rqworker software_manager &
/opt/netbox/venv/bin/python /opt/netbox/netbox/manage.py rqworker software_manager &
/opt/netbox/venv/bin/python /opt/netbox/netbox/manage.py rqworker software_manager &
/opt/netbox/venv/bin/python /opt/netbox/netbox/manage.py rqworker software_manager &

/opt/netbox/venv/bin/python /opt/netbox/netbox/manage.py rqscheduler &

/opt/netbox/venv/bin/python /opt/netbox/netbox/manage.py rqworker check_releases default
exec "$@"
