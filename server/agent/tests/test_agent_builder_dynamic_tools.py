import asyncio
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from enthusiast_common.agents import BaseAgent
from enthusiast_common.builder import AgentBuilder
from enthusiast_common.integrations import BaseToolProvidingIntegration
from langchain_core.tools import StructuredTool
from pydantic import BaseModel


class ToolArgs(BaseModel):
    value: str


def stub_tool(name: str) -> StructuredTool:
    return StructuredTool.from_function(func=lambda value: value, name=name, description=name, args_schema=ToolArgs)


def tool_names(tools) -> list[str]:
    return [tool.name for tool in tools]


class StubToolProvidingIntegration(BaseToolProvidingIntegration):
    TYPE = "stub"
    NAME = "Stub"

    def __init__(self, tools=None, error=None, delay=0):
        self._stub_tools = tools or []
        self._error = error
        self._delay = delay

    async def get_tools(self):
        if self._error:
            raise self._error
        if self._delay:
            await asyncio.sleep(self._delay)
        return self._stub_tools


class StubAgent(BaseAgent):
    NAME = "Stub"
    AGENT_KEY = "stub"

    def get_answer(self, input_text: str) -> str:
        return ""

    async def aget_answer(self, input_text: str) -> str:
        return ""


def agent_with_tools(*names: str) -> StubAgent:
    """An agent whose own tools carry *names*, standing in for its built-in toolset."""
    return StubAgent(
        tools=[SimpleNamespace(NAME=name) for name in names],
        llm=None,
        system_prompt="",
        conversation_id=1,
        injector=None,
    )


class TestSetDynamicTools:
    def test_keeps_tools_whose_names_are_free(self):
        agent = agent_with_tools("product_search")

        agent.set_dynamic_tools([stub_tool("weather"), stub_tool("calendar")])

        assert tool_names(agent._dynamic_tools) == ["weather", "calendar"]

    def test_drops_a_tool_that_would_shadow_a_built_in_one(self):
        """A connected server must never be able to take over a name the agent already relies on."""
        agent = agent_with_tools("product_search")

        agent.set_dynamic_tools([stub_tool("product_search"), stub_tool("weather")])

        assert tool_names(agent._dynamic_tools) == ["weather"]

    def test_keeps_only_the_first_of_two_integrations_claiming_one_name(self):
        agent = agent_with_tools()

        agent.set_dynamic_tools([stub_tool("search"), stub_tool("search"), stub_tool("other")])

        assert tool_names(agent._dynamic_tools) == ["search", "other"]


class TestAgentBuilderBuildDynamicTools:
    def _make_builder(self, resolver_cls):
        config = MagicMock()
        config.integration_plugin_resolver = resolver_cls
        builder = AgentBuilder(config=config, conversation_id=1)
        builder._data_set_id = 42
        return builder

    def _builder_returning(self, integrations):
        resolver_instance = MagicMock()
        resolver_instance.resolve_all.return_value = integrations
        return self._make_builder(resolver_cls=MagicMock(return_value=resolver_instance))

    def test_returns_empty_list_when_no_resolver_configured(self):
        builder = self._make_builder(resolver_cls=None)

        tools = asyncio.run(builder._build_dynamic_tools())

        assert tools == []

    def test_merges_tools_from_every_reachable_integration(self):
        builder = self._builder_returning(
            [
                StubToolProvidingIntegration(tools=[stub_tool("a"), stub_tool("b")]),
                StubToolProvidingIntegration(tools=[stub_tool("c")]),
            ]
        )

        tools = asyncio.run(builder._build_dynamic_tools())

        assert tool_names(tools) == ["a", "b", "c"]

    def test_one_unreachable_integration_does_not_block_the_others(self):
        builder = self._builder_returning(
            [
                StubToolProvidingIntegration(error=ConnectionError("server down")),
                StubToolProvidingIntegration(tools=[stub_tool("still_works")]),
            ]
        )

        tools = asyncio.run(builder._build_dynamic_tools())

        assert tool_names(tools) == ["still_works"]

    @patch("enthusiast_common.builder.default.DYNAMIC_TOOL_FETCH_TIMEOUT_SECONDS", 0.01)
    def test_an_integration_that_answers_too_slowly_is_skipped(self):
        builder = self._builder_returning(
            [
                StubToolProvidingIntegration(tools=[stub_tool("too_slow")], delay=5),
                StubToolProvidingIntegration(tools=[stub_tool("prompt")]),
            ]
        )

        tools = asyncio.run(builder._build_dynamic_tools())

        assert tool_names(tools) == ["prompt"]

    def test_integrations_are_fetched_concurrently(self):
        """Each integration waits on the other, so this can only finish if both are in flight.

        Fetched one after another, the first would still be waiting on a signal the second has not
        run to send, and would drop out on its timeout leaving a single tool behind.
        """
        first_arrived, second_arrived = asyncio.Event(), asyncio.Event()

        class CoordinatingIntegration(StubToolProvidingIntegration):
            def __init__(self, tools, arrive, wait_for):
                super().__init__(tools=tools)
                self._arrive = arrive
                self._wait_for = wait_for

            async def get_tools(self):
                self._arrive.set()
                await self._wait_for.wait()
                return self._stub_tools

        builder = self._builder_returning(
            [
                CoordinatingIntegration([stub_tool("first")], first_arrived, second_arrived),
                CoordinatingIntegration([stub_tool("second")], second_arrived, first_arrived),
            ]
        )

        tools = asyncio.run(builder._build_dynamic_tools())

        assert tool_names(tools) == ["first", "second"]
