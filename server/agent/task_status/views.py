from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from utils.views.task_status import TaskStatusView

from account.authorization import PERMISSIONS, has_dataset_perm
from agent.conversation.tasks import TaskType
from agent.models import Conversation
from agent.task_status.serializers import FileUploadTaskStatusSerializer, MessagePushTaskStatusSerializer


class ConversationTaskStatusView(TaskStatusView):
    """Task status whose result is revealed to the conversation's owner or holders of CONVERSATION.VIEW_ALL."""

    def _is_result_visible(self, user, result):
        if not isinstance(result, dict) or result.get("task_type") != self.task_type:
            return False

        conversation = Conversation.objects.select_related("data_set").filter(id=result.get("conversation_id")).first()
        if conversation is None:
            return False

        return conversation.user_id == user.id or has_dataset_perm(
            user, PERMISSIONS.CONVERSATION.VIEW_ALL, conversation.data_set
        )


class FileUploadStatusView(ConversationTaskStatusView):
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


class MessagePushStatusView(ConversationTaskStatusView):
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
