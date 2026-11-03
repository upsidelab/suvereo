import asyncio
from datetime import datetime
from typing import Optional

from suvereo_common.agentic_execution.memory import ToolScratchpad
from suvereo_common.integrations import BaseToolProvidingIntegration

from account.models import User
from agent.core.agents.config_overrides import AgentConfigOverrides
from agent.core.agents.default_config import get_default_config
from agent.core.registries.agents.agent_registry import AgentRegistry
from agent.models import Conversation, Message
from agent.models.agent import Agent
from catalog.models import DataSet


class ConversationManager:
    DEFAULT_ERROR_MESSAGE = "We couldn't process your request at this time"

    def get_answer(
        self,
        conversation: Conversation,
        question_message: str,
        streaming: bool,
        tool_scratchpad: Optional[ToolScratchpad] = None,
        overrides: Optional[AgentConfigOverrides] = None,
    ) -> str:
        """Formulate an answer to a given question and store the decision-making process.

        Engine calculates embedding for a question and using similarity search collects documents that may contain
        relevant content.
        """
        if self._should_answer_asynchronously(conversation, overrides):
            return asyncio.run(
                self._get_answer_async(
                    conversation, question_message, streaming, tool_scratchpad, overrides
                )
            )

        agent = AgentRegistry().get_conversation_agent(
            conversation,
            streaming,
            tool_scratchpad=tool_scratchpad,
            overrides=overrides,
        )
        response = agent.get_answer(question_message)

        return response

    def _should_answer_asynchronously(
        self, conversation: Conversation, overrides: Optional[AgentConfigOverrides] = None
    ) -> bool:
        """Decide whether this turn needs the async path, which exists to await the tools of tool-providing integrations.

        The agent has to have at least one tool-providing integration (e.g. an MCP server) selected
        (`Agent.tool_providing_integrations`); any other turn never pays for an event loop it has no use for.

        The resolver comes from the default agent config rather than being imported directly, so a
        host that swaps its implementation is honoured here as well as in the agent builder; a run's
        overrides win over both, so an evaluation asks its own resolver.
        """
        resolver_class = (overrides and overrides.integration_plugin_resolver) or get_default_config().integration_plugin_resolver
        if resolver_class is None:
            return False
        return resolver_class().has_any_for_agent(conversation.agent_id, BaseToolProvidingIntegration)

    async def _get_answer_async(
        self,
        conversation: Conversation,
        question_message: str,
        streaming: bool,
        tool_scratchpad: Optional[ToolScratchpad],
        overrides: Optional[AgentConfigOverrides] = None,
    ) -> str:
        agent = await AgentRegistry().aget_conversation_agent(
            conversation,
            streaming,
            tool_scratchpad=tool_scratchpad,
            overrides=overrides,
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
