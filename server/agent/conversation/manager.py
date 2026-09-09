import asyncio
from datetime import datetime
from typing import Optional

from enthusiast_common.agentic_execution.memory import ToolScratchpad
from enthusiast_common.agents import ConfigType
from enthusiast_common.integrations import BaseToolProvidingIntegration

from account.models import User
from agent.core.registries.agents.agent_registry import AgentRegistry
from agent.models import Conversation, Message
from agent.models.agent import Agent
from catalog.integrations.resolver import IntegrationPluginResolver
from catalog.models import DataSet


class ConversationManager:
    DEFAULT_ERROR_MESSAGE = "We couldn't process your request at this time"

    def get_answer(
        self,
        conversation: Conversation,
        question_message: str,
        streaming: bool,
        config_type: ConfigType = ConfigType.CONVERSATION,
        tool_scratchpad: Optional[ToolScratchpad] = None,
    ) -> str:
        """Formulate an answer to a given question and store the decision-making process.

        Engine calculates embedding for a question and using similarity search collects documents that may contain
        relevant content.
        """
        # Resolving the agent class here, before branching, also has the side effect of populating
        # conversation.agent's cache (get_conversation() already select_related()s it, so this
        # is not even a fresh query) — the async path re-reads conversation.agent.agent_type
        # later, and it must hit that cache rather than issue a fresh sync query from inside a
        # running event loop.
        agent_class = AgentRegistry().get_agent_class_by_type(conversation.agent.agent_type)
        if self._should_answer_asynchronously(conversation, agent_class):
            return asyncio.run(
                self._get_answer_async(conversation, question_message, streaming, config_type, tool_scratchpad)
            )

        agent = AgentRegistry().get_conversation_agent(
            conversation,
            streaming,
            config_type=config_type,
            tool_scratchpad=tool_scratchpad,
        )
        response = agent.get_answer(question_message)

        return response

    def _should_answer_asynchronously(self, conversation: Conversation, agent_class: type) -> bool:
        """Decide whether this turn needs the async path, which exists to await integration tools.

        Two things have to hold: the agent has to be able to answer asynchronously at all, and the
        data set has to have at least one tool-providing integration (e.g. an MCP server) whose
        tools are worth fetching. Agents that only implement ``get_answer`` keep the sync path, and
        a data set with nothing connected never pays for an event loop it has no use for.
        """
        if not hasattr(agent_class, "aget_answer"):
            return False
        return IntegrationPluginResolver().has_any(conversation.data_set_id, BaseToolProvidingIntegration)

    async def _get_answer_async(
        self,
        conversation: Conversation,
        question_message: str,
        streaming: bool,
        config_type: ConfigType,
        tool_scratchpad: Optional[ToolScratchpad],
    ) -> str:
        agent = await AgentRegistry().aget_conversation_agent(
            conversation,
            streaming,
            config_type=config_type,
            tool_scratchpad=tool_scratchpad,
        )
        return await agent.aget_answer(question_message)

    def create_conversation(self, user_id: int, agent_id: int) -> Conversation:
        user = User.objects.get(id=user_id)
        agent = Agent.objects.get(id=agent_id)

        conversation = Conversation.objects.create(
            started_at=datetime.now(),
            user=user,
            data_set=agent.dataset,
            agent=agent,
        )
        return conversation

    def get_conversation(self, user_id: int, data_set_id: int, conversation_id: int) -> Conversation:
        user = User.objects.get(id=user_id)
        data_set = DataSet.objects.get(id=data_set_id)
        return Conversation.objects.select_related("agent").get(id=conversation_id, data_set=data_set, user=user)

    def respond_to_user_message(
        self, conversation_id: int, data_set_id: int, user_id: int, message: str, streaming: bool
    ) -> Message:
        conversation = self.get_conversation(user_id=user_id, data_set_id=data_set_id, conversation_id=conversation_id)

        # Set the conversation summary if it's the first message
        if not conversation.summary:
            conversation.summary = message
            conversation.save()

        self.get_answer(conversation, message, streaming)
        response = conversation.messages.order_by("created_at").last()

        return response

    def record_error(self, conversation_id: int, user_id: int, data_set_id: int, error: Exception):
        conversation = self.get_conversation(user_id=user_id, data_set_id=data_set_id, conversation_id=conversation_id)
        user_message = conversation.messages.order_by("-created_at").first()
        user_message.answer_failed = True
        user_message.save()
        Message.objects.create(
            conversation=conversation,
            created_at=datetime.now(),
            type=Message.MessageType.SYSTEM,
            text=self.DEFAULT_ERROR_MESSAGE,
        )
