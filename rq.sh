#!/bin/bash
/opt/netbox/venv/bin/python /opt/netbox/netbox/manage.py rqworker software_manager &
/opt/netbox/venv/bin/python /opt/netbox/netbox/manage.py rqworker software_manager &
/opt/netbox/venv/bin/python /opt/netbox/netbox/manage.py rqworker software_manager &
/opt/netbox/venv/bin/python /opt/netbox/netbox/manage.py rqworker software_manager &
/opt/netbox/venv/bin/python /opt/netbox/netbox/manage.py rqworker software_manager &

/opt/netbox/venv/bin/python /opt/netbox/netbox/manage.py rqworker high default low
exec "$@"
