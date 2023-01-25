FROM netboxcommunity/netbox:v3.4.3-2.4.0

COPY requirements.txt /requirements.txt
RUN /opt/netbox/venv/bin/python -m pip install -r /requirements.txt

RUN mkdir /opt/netbox/netbox/media/software-images/
RUN chown -R unit:unit /opt/netbox/netbox/media/software-images

RUN echo '\n\
RQ_QUEUES["software_manager"]=RQ_PARAMS\n\
' >> /opt/netbox/netbox/netbox/settings.py

#--SoftwareManager
COPY ./software_manager/ /source/SoftwareManager/software_manager/
COPY ./setup.py /source/SoftwareManager/
COPY ./README.md /source/SoftwareManager/
COPY ./MANIFEST.in /source/SoftwareManager/

#--Pip
RUN /opt/netbox/venv/bin/python -m pip install /source/SoftwareManager/

