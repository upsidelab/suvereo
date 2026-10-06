from datetime import datetime, timedelta
from enum import StrEnum

from asgiref.sync import async_to_sync
from celery import Task, shared_task
from channels.layers import get_channel_layer
from django.core.files.base import ContentFile
from django.utils import timezone

from agent.conversation.manager import ConversationManager
from agent.conversation.serializers import ConversationFileSerializer
from agent.conversation.services import FileParsingService
from agent.core.callbacks import BaseWebSocketHandler
from agent.models import Message
from agent.models.conversation import Conversation, ConversationFile
from pecl import settings


class TaskType(StrEnum):
    """Identifies which job produced a background task's result, so a task's status can only be
    read back through the endpoint meant for that job type."""

    MESSAGE_PUSH = "message_push"
    FILE_UPLOAD = "file_upload"


class TaskStatus(StrEnum):
    PENDING = "PENDING"
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"


class SaveMessageOnFailureTask(Task):
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        conversation_id = kwargs.get("conversation_id")
        data_set_id = kwargs.get("data_set_id")
        user_id = kwargs.get("user_id")
        message = kwargs.get("message")

        Message.objects.create(
            conversation_id=conversation_id,
            created_at=datetime.now(),
            type=Message.MessageType.HUMAN,
            text=message,
            answer_failed=True,
        )

        manager = ConversationManager()
        manager.record_error(conversation_id, user_id, data_set_id, exc)
        ws_handler = BaseWebSocketHandler(conversation_id=conversation_id)
        ws_handler.send_message({"type": "chat_message", "event": "error", "output": manager.DEFAULT_ERROR_MESSAGE})


@shared_task(base=SaveMessageOnFailureTask, bind=True, max_retries=3)
def respond_to_user_message_task(
    self, conversation_id: int, data_set_id: int, user_id: int, message: str, streaming: bool
):
    manager = ConversationManager()
    try:
        answer = manager.respond_to_user_message(
            conversation_id=conversation_id,
            data_set_id=data_set_id,
            user_id=user_id,
            message=message,
            streaming=streaming,
        )
        if streaming:
            channel_layer = get_channel_layer()
            group_name = f"conversation_{conversation_id}"
            async_to_sync(channel_layer.group_send)(
                group_name,
                {
                    "type": "chat_message",
                    "event": "message_created",
                    "answer_id": answer.id,
                },
            )
        return {"task_type": TaskType.MESSAGE_PUSH, "conversation_id": conversation_id, "message_id": answer.id}
    except Exception:
        self.retry(countdown=1)


@shared_task
def process_file_upload_task(conversation_id: int, file_content: bytes, filename: str, content_type: str):
    try:
        conversation = Conversation.objects.get(id=conversation_id)
        django_file = ContentFile(file_content, name=filename)
        file_category = "image" if content_type.startswith("image/") else "file"

        obj = ConversationFile(
            conversation=conversation,
            file=django_file,
            content_type=content_type,
            file_category=file_category,
            llm_content=FileParsingService(django_file, content_type).process() or "",
        )

        obj.save()

        serializer = ConversationFileSerializer(obj)

        return {
            "task_type": TaskType.FILE_UPLOAD,
            "status": TaskStatus.SUCCESS,
            "conversation_id": conversation_id,
            "uploaded_file": serializer.data,
            "file_id": obj.id,
        }

    except Conversation.DoesNotExist:
        return {
            "task_type": TaskType.FILE_UPLOAD,
            "status": TaskStatus.FAILURE,
            "conversation_id": conversation_id,
            "error": f"Conversation {conversation_id} not found",
        }
    except Exception as e:
        return {
            "task_type": TaskType.FILE_UPLOAD,
            "status": TaskStatus.FAILURE,
            "conversation_id": conversation_id,
            "error": str(e),
        }


@shared_task
def clean_uploaded_files():
    ConversationFile.objects.filter(
        created_at__lt=timezone.now() - timedelta(hours=settings.UPLOADED_FILE_RETENTION_PERIOD_HOURS)
    ).delete()
