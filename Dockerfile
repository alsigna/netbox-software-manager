FROM netboxcommunity/netbox:latest-ldap

COPY requirements.txt /requirements.txt
RUN /opt/netbox/venv/bin/python -m pip install -r /requirements.txt

RUN mkdir /opt/netbox/netbox/media/software-images/
RUN chown -R unit:unit /opt/netbox/netbox/media/software-images

# RUN mkdir /var/lib/unit/.ssh
# RUN chown -R unit:unit /var/lib/unit/.ssh

# RUN echo $'\n\
# Host * \n\                                                                                                                                   
#      KexAlgorithms +diffie-hellman-group1-sha1,diffie-hellman-group-exchange-sha1\n\
#      Ciphers +aes128-cbc,3des-cbc,aes192-cbc,aes256-cbc\n\
# ' > /var/lib/unit/.ssh/config
# RUN chown -R unit:unit /var/lib/unit/.ssh


RUN echo $'\n\
RQ_QUEUES["software_manager"]=RQ_PARAMS\n\
' >> /opt/netbox/netbox/netbox/settings.py

#--SoftwareManager
COPY ./software_manager/ /source/SoftwareManager/software_manager/
COPY ./setup.py /source/SoftwareManager/
COPY ./README.md /source/SoftwareManager/
COPY ./MANIFEST.in /source/SoftwareManager/

#--Pip
RUN /opt/netbox/venv/bin/python -m pip install /source/SoftwareManager/

