from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import UploadedFile

from agent.agentic_execution.registry import AgenticExecutionDefinitionRegistry
from agent.agentic_execution.tasks import run_agentic_execution_task
from agent.conversation.services import (
    ConversationFileAttachService,
    FileUploadNotSupportedError,
    UnsupportedFileTypeError,
)
from agent.models.agent import Agent
from agent.models.agentic_execution import AgenticExecution
from agent.models.conversation import Conversation

User = get_user_model()

__all__ = ["AgenticExecutionService", "FileUploadNotSupportedError", "UnsupportedFileTypeError"]


class AgenticExecutionService:
    """Orchestrates the creation of an AgenticExecution and its associated resources."""

    def start(
        self,
        agent: Agent,
        user: User,
        execution_key: str,
        validated_input: dict,
        uploaded_files: list[UploadedFile],
    ) -> AgenticExecution:
        files = ConversationFileAttachService()
        files.validate(agent, [f.name for f in uploaded_files])

        conversation = Conversation.objects.create(
            user=user,
            data_set=agent.dataset,
            agent=agent,
        )

        for f in uploaded_files:
            files.attach(conversation, f.name, f.read(), getattr(f, "content_type", "") or "")

        execution = AgenticExecution.objects.create(
            agent=agent,
            execution_key=execution_key,
            conversation=conversation,
            input=validated_input,
        )
        task = run_agentic_execution_task.delay(execution.pk)
        execution.celery_task_id = task.id
        execution.save(update_fields=["celery_task_id"])

        return execution

    def get_execution_types(self, agent: Agent) -> list:
        """Return all registered agentic execution definition classes for the given agent type."""
        return AgenticExecutionDefinitionRegistry().get_by_agent_type(agent.agent_type)
