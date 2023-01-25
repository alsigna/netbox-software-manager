from netbox.api.viewsets import NetBoxModelViewSet

from ..filtersets import SoftwareImageFilterSet
from ..models import GoldenImage, ScheduledTask, SoftwareImage
from .serializers import GoldenImageSerializer, ScheduledTaskSerializer, SoftwareImageSerializer


class SoftwareImageViewSet(NetBoxModelViewSet):
    queryset = SoftwareImage.objects.all()
    serializer_class = SoftwareImageSerializer
    filterset_class = SoftwareImageFilterSet


class GoldenImageViewSet(NetBoxModelViewSet):
    queryset = GoldenImage.objects.all()
    serializer_class = GoldenImageSerializer


class ScheduledTaskViewSet(NetBoxModelViewSet):
    queryset = ScheduledTask.objects.all()
    serializer_class = ScheduledTaskSerializer
