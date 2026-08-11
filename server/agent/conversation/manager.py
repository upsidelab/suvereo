import asyncio
from datetime import datetime
from typing import Optional

from enthusiast_common.agentic_execution.memory import ToolScratchpad
from enthusiast_common.agents import ConfigType

from account.models import User
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
        config_type: ConfigType = ConfigType.CONVERSATION,
        tool_scratchpad: Optional[ToolScratchpad] = None,
    ) -> str:
        """Formulate an answer to a given question and store the decision-making process.

        Engine calculates embedding for a question and using similarity search collects documents that may contain
        relevant content.
        """
        # Checking the flag here, before branching, also has the side effect of populating
        # conversation.agent's cache (get_conversation() already select_related()s it, so this
        # is not even a fresh query) — the async path re-reads conversation.agent.agent_type
        # later, and it must hit that cache rather than issue a fresh sync query from inside a
        # running event loop.
        agent_type = conversation.agent.agent_type
        agent_class = AgentRegistry().get_agent_class_by_type(agent_type)
        if getattr(agent_class, "MCP_TOOLS_ENABLED", False):
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
