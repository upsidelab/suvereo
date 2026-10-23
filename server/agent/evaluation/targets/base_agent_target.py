import logging
from abc import ABC, abstractmethod

from enthusiast_common.integrations import BaseIntegrationPluginResolver

from account.models import User
from agent.evaluation.abandoned_runs import AbandonedRuns
from agent.models import Agent, Conversation
from agent.services import ConversationDeletionService

logger = logging.getLogger(__name__)

SUMMARY = "Evaluation run"


class BaseAgentTarget(ABC):
    """The agent a suite runs against; opened once per suite, it hands out one conversation per run.

    keep_run_data leaves what the runs created (conversations, and a sandbox's whole DataSet) for inspection.
    """

    def __init__(self, user: User, keep_run_data: bool = False):
        self.user = user
        self.keep_run_data = keep_run_data
        self.agent: Agent | None = None
        self._conversation_ids: list[int] = []

    @property
    @abstractmethod
    def real_resolver(self) -> type[BaseIntegrationPluginResolver] | None:
        """The resolver for integrations no mock covers; None refuses real integrations."""

    @abstractmethod
    def open(self) -> Agent:
        """Prepare the agent and return it."""

    def close(self) -> None:
        """Delete the runs' conversations, or mark them kept; a failure is logged so it never hides the run's error."""
        conversations = Conversation.all_objects.filter(id__in=self._conversation_ids)
        try:
            if self.keep_run_data:
                conversations.update(is_temporary=False)
            else:
                ConversationDeletionService.delete(conversations)
        except Exception:
            logger.exception("Could not clean up the evaluation conversations of agent %s", self.agent)
        finally:
            self._conversation_ids.clear()

    def new_conversation(self) -> Conversation:
        conversation = Conversation.objects.create(
            user=self.user, data_set=self.agent.dataset, agent=self.agent, summary=SUMMARY, is_temporary=True
        )
        self._conversation_ids.append(conversation.id)
        return conversation

    def purge_abandoned_runs(self) -> None:
        """Delete what runs that died left behind: their sandboxes, and their conversations on real DataSets."""
        try:
            AbandonedRuns.purge()
        except Exception:
            logger.exception("Could not purge abandoned evaluation runs")

    def __enter__(self) -> "BaseAgentTarget":
        """Purge abandoned runs, then open the agent."""
        self.purge_abandoned_runs()
        self.agent = self.open()
        return self

    def __exit__(self, *exc_info) -> None:
        self.close()
