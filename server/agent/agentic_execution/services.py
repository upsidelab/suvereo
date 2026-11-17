import logging
from uuid import uuid4

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import UploadedFile
from django.db import transaction
from suvereo_common.agentic_execution import ExecutionFailureCode

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
logger = logging.getLogger(__name__)

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
            celery_task_id=str(uuid4()),
        )
        transaction.on_commit(lambda: self._queue(execution))

        return execution

    @staticmethod
    def _queue(execution: AgenticExecution) -> None:
        try:
            run_agentic_execution_task.apply_async(args=(execution.pk,), task_id=execution.celery_task_id)
        except Exception as e:
            logger.exception("Could not queue agentic execution %s", execution.pk)
            execution.mark_failed(
                failure_code=ExecutionFailureCode.RUNTIME_ERROR,
                failure_explanation=f"Could not queue the execution: {type(e).__name__}: {e}",
            )

    def get_execution_types(self, agent: Agent) -> list:
        """Return all registered agentic execution definition classes for the given agent type."""
        return AgenticExecutionDefinitionRegistry().get_by_agent_type(agent.agent_type)
