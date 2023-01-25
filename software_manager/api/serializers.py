# from django.contrib.auth.models import User
# from django.contrib.contenttypes.models import ContentType
# from django.core.exceptions import ObjectDoesNotExist
# from drf_yasg.utils import swagger_serializer_method
# from rest_framework import serializers

# from dcim.api.nested_serializers import (
#     NestedDeviceRoleSerializer,
#     NestedDeviceTypeSerializer,
#     NestedPlatformSerializer,
#     NestedRegionSerializer,
#     NestedSiteSerializer,
#     NestedSiteGroupSerializer,
# )
# from dcim.models import DeviceRole, DeviceType, Platform, Region, Site, SiteGroup
# from extras.choices import *
# from extras.models import *
# from extras.utils import FeatureQuery
# from netbox.api import ChoiceField, ContentTypeField, SerializedPKRelatedField
# from netbox.api.exceptions import SerializerNotFound
# from netbox.api.serializers import BaseModelSerializer, NetBoxModelSerializer, ValidatedModelSerializer
# from tenancy.api.nested_serializers import NestedTenantSerializer, NestedTenantGroupSerializer
# from tenancy.models import Tenant, TenantGroup
# from users.api.nested_serializers import NestedUserSerializer
# from utilities.api import get_serializer_for_model
# from virtualization.api.nested_serializers import (
#     NestedClusterGroupSerializer,
#     NestedClusterSerializer,
#     NestedClusterTypeSerializer,
# )
# from virtualization.models import Cluster, ClusterGroup, ClusterType
# from .nested_serializers import *


from netbox.api.serializers import ValidatedModelSerializer
from rest_framework import serializers

# from netbox.api import ContentTypeField
from ..models import GoldenImage, ScheduledTask, SoftwareImage

# from django.contrib.contenttypes.models import ContentType


class SoftwareImageSerializer(ValidatedModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="plugins-api:software_manager-api:softwareimage-detail")

    class Meta:
        model = SoftwareImage
        fields = [
            "id",
            "url",
            "created",
            "last_updated",
            "image",
            "supported_devicetypes",
            "md5sum",
            "md5sum_calculated",
            "version",
            "filename",
        ]


class GoldenImageSerializer(ValidatedModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="plugins-api:software_manager-api:goldenimage-detail")

    class Meta:
        model = GoldenImage
        fields = [
            "id",
            "url",
            "created",
            "last_updated",
            "pid",
            "sw",
        ]


class ScheduledTaskSerializer(ValidatedModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="plugins-api:software_manager-api:scheduledtask-detail")

    class Meta:
        model = ScheduledTask
        fields = [
            "id",
            "url",
            "created",
            "last_updated",
            "job_id",
            "status",
        ]
