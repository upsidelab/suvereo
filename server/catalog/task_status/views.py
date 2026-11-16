from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from utils.views.task_status import TaskStatusView

from account.authorization import PERMISSIONS, has_dataset_perm
from catalog.models import DataSet
from catalog.task_status.task_types import CatalogTaskType

from .serializers import IntegrationSyncTaskStatusSerializer


class IntegrationSyncStatusView(TaskStatusView):
    """Status of an integration sync, revealed to holders of INTEGRATION.VIEW on the integration's data set."""

    task_type = CatalogTaskType.INTEGRATION_SYNC
    response_serializer_class = IntegrationSyncTaskStatusSerializer

    def _is_result_visible(self, user, result):
        if not isinstance(result, dict) or result.get("task_type") != self.task_type:
            return False

        data_set = DataSet.objects.filter(id=result.get("data_set_id")).first()
        return data_set is not None and has_dataset_perm(user, PERMISSIONS.INTEGRATION.VIEW, data_set)

    @swagger_auto_schema(
        operation_description="Check the status of an integration sync task",
        manual_parameters=[
            openapi.Parameter(
                "task_id", openapi.IN_PATH, description="ID of the integration sync task", type=openapi.TYPE_STRING
            )
        ],
        responses={200: IntegrationSyncTaskStatusSerializer()},
    )
    def get(self, request, task_id, *args, **kwargs):
        return super().get(request, task_id, *args, **kwargs)
