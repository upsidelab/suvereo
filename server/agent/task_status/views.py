from celery.result import AsyncResult
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from account.authorization import PERMISSIONS, has_dataset_perm
from agent.models import Conversation
from agent.tasks import TaskStatus, TaskType

from .serializers import FileUploadTaskStatusSerializer, MessagePushTaskStatusSerializer


class TaskStatusView(APIView):
    """
    Base view to check the status of an enqueued task running in the background.

    Only reports on tasks of `task_type` (subclasses must set it) - a task_id belonging to a
    different job, or to no job we recognise, is reported as PENDING rather than 404, matching
    Celery's own behaviour for unknown ids and avoiding confirming or denying its existence.
    Once the task has succeeded, the result is only revealed to a requester who owns the
    conversation it belongs to, or who holds the VIEW_ALL permission on its dataset - anyone
    else also sees PENDING.
    """

    permission_classes = [IsAuthenticated]
    task_type: TaskType
    response_serializer_class: type

    def get(self, request, task_id, *args, **kwargs):
        try:
            task_result = AsyncResult(task_id)

            response_data = {
                "task_id": task_id,
                "status": task_result.status,
            }

            if task_result.status == TaskStatus.SUCCESS:
                result = task_result.result
                if self._is_result_visible(request.user, result):
                    response_data["result"] = result
                else:
                    response_data["status"] = TaskStatus.PENDING
            elif task_result.status == TaskStatus.FAILURE:
                response_data["result"] = {"error": str(task_result.result)}

            serializer = self.response_serializer_class(response_data)
            return Response(serializer.data, status=status.HTTP_200_OK)

        except Exception as e:
            return Response(
                {"error": f"Failed to get task status: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def _is_result_visible(self, user, result):
        if not isinstance(result, dict) or result.get("task_type") != self.task_type:
            return False

        conversation = Conversation.objects.select_related("data_set").filter(id=result.get("conversation_id")).first()
        if conversation is None:
            return False

        return conversation.user_id == user.id or has_dataset_perm(
            user, PERMISSIONS.CONVERSATION.VIEW_ALL, conversation.data_set
        )


class FileUploadStatusView(TaskStatusView):
    task_type = TaskType.FILE_UPLOAD
    response_serializer_class = FileUploadTaskStatusSerializer

    @swagger_auto_schema(
        operation_description="Check the status of a file upload task",
        manual_parameters=[
            openapi.Parameter(
                "task_id", openapi.IN_PATH, description="ID of the file upload task", type=openapi.TYPE_STRING
            )
        ],
        responses={200: FileUploadTaskStatusSerializer()},
    )
    def get(self, request, task_id, *args, **kwargs):
        return super().get(request, task_id, *args, **kwargs)


class MessagePushStatusView(TaskStatusView):
    task_type = TaskType.MESSAGE_PUSH
    response_serializer_class = MessagePushTaskStatusSerializer

    @swagger_auto_schema(
        operation_description="Check the status of a message push task",
        manual_parameters=[
            openapi.Parameter(
                "task_id", openapi.IN_PATH, description="ID of the message push task", type=openapi.TYPE_STRING
            )
        ],
        responses={200: MessagePushTaskStatusSerializer()},
    )
    def get(self, request, task_id, *args, **kwargs):
        return super().get(request, task_id, *args, **kwargs)
