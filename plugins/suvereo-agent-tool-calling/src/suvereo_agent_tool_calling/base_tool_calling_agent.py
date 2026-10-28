from typing import Any

from suvereo_agent_tools import FileListTool, FileRetrievalTool
from suvereo_common.agents import BaseAgent
from suvereo_common.utils import run_off_event_loop
from langchain.agents import create_agent
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langchain_core.tools import BaseTool
from langgraph.graph.state import CompiledStateGraph

from suvereo_agent_tool_calling.context_window_builder import ContextWindowBuilder


class BaseToolCallingAgent(BaseAgent):
    __abstract__ = True

    DEFAULT_FILE_TOOLS = [FileListTool, FileRetrievalTool]

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        if getattr(cls, "FILE_UPLOAD", False):
            from suvereo_common.config import FileToolConfig

            cls.TOOLS = getattr(cls, "TOOLS", []) + [
                FileToolConfig(tool_class=file_tool_class) for file_tool_class in cls.DEFAULT_FILE_TOOLS
            ]

    def get_answer(self, input_text: str) -> str:
        context_messages = self._build_context_messages()
        result = self._build_agent().invoke(
            {"messages": self._build_input_messages(context_messages, input_text)},
            config=self._build_invoke_config(),
        )
        return self._record_turn(result, context_messages)

    async def aget_answer(self, input_text: str) -> str:
        """Async twin of get_answer(): uses ainvoke() so dynamic tools (e.g. MCP) can be awaited.

        The steps that touch the database run in a worker thread, since they are the synchronous
        ORM calls that must not happen on a thread with a running event loop.
        """
        context_messages = await run_off_event_loop(self._build_context_messages)
        result = await self._build_agent().ainvoke(
            {"messages": self._build_input_messages(context_messages, input_text)},
            config=self._build_invoke_config(),
        )
        return await run_off_event_loop(self._record_turn, result, context_messages)

    def _build_input_messages(self, context_messages: list[BaseMessage], input_text: str) -> list[BaseMessage]:
        return context_messages + [HumanMessage(content=input_text)]

    def _record_turn(self, result: dict[str, Any], context_messages: list[BaseMessage]) -> str:
        """Store everything this turn produced and return the agent's final answer.

        The answer is picked out before anything is written, so a run that never produced a final
        message leaves the history untouched rather than half-written.
        """
        new_messages = result["messages"][len(context_messages):]
        final_message = next(
            m for m in reversed(new_messages)
            if isinstance(m, AIMessage) and not m.tool_calls
        )

        self._injector.chat_history.add_messages(new_messages)

        if compactor := self._injector.memory_compactor:
            compactor.compact_if_needed()

        return final_message.text

    def _build_context_messages(self) -> list[BaseMessage]:
        return ContextWindowBuilder(
            chat_history=self._injector.chat_history,
            memory_compactor=self._injector.memory_compactor,
        ).build(max_tokens=self._conversation_history_token_limit)

    def _build_tools(self) -> list[BaseTool]:
        return [tool.as_tool() for tool in self._tools] + self._dynamic_tools

    def _build_invoke_config(self) -> dict[str, Any]:
        if self._callback_handler:
            return {"callbacks": [self._callback_handler]}

        return {}

    def _build_agent(self) -> CompiledStateGraph:
        return create_agent(
            model=self._llm,
            tools=self._build_tools(),
            system_prompt=self._get_system_prompt(),
        )
