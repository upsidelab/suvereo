from abc import ABC, abstractmethod

from enthusiast_common.integrations import BaseIntegrationPluginResolver

from account.models import User
from agent.evaluation.eval_conversations import EvalConversations
from agent.models import Agent, Conversation


class BaseAgentTarget(ABC):
    """The agent a suite runs against; opened once per suite, it hands out one conversation per run."""

    def __init__(self, user: User, keep_conversations: bool = False):
        self.user = user
        self.keep_conversations = keep_conversations
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
        """Delete the runs' conversations unless they are to be kept."""
        if not self.keep_conversations:
            EvalConversations.delete(Conversation.objects.filter(id__in=self._conversation_ids))
        self._conversation_ids.clear()

    def new_conversation(self) -> Conversation:
        conversation = EvalConversations.create(self.agent, self.user)
        self._conversation_ids.append(conversation.id)
        return conversation

    def __enter__(self) -> "BaseAgentTarget":
        self.agent = self.open()
        return self

    def __exit__(self, *exc_info) -> None:
        self.close()
