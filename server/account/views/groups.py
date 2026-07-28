from django.contrib.auth.models import Group
from drf_yasg.utils import swagger_auto_schema
from rest_framework.generics import ListAPIView

from account.authorization import PERM_MANAGE_DATASETS
from account.permissions import HasRequiredPermission
from account.serializers import GroupSerializer


class GroupListView(ListAPIView):
    """Read-only list of Django Groups, for populating the dataset-access target picker.

    Creating/editing groups themselves stays a Django-admin-site operation.
    """

    permission_classes = [HasRequiredPermission]
    required_permission = PERM_MANAGE_DATASETS
    serializer_class = GroupSerializer
    queryset = Group.objects.all().order_by("name")
    pagination_class = None

    @swagger_auto_schema(operation_description="List all groups")
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)
