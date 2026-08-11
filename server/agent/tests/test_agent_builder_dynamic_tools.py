import asyncio
from unittest.mock import MagicMock

from enthusiast_common.builder import AgentBuilder
from enthusiast_common.integrations import BaseToolProvidingIntegration


class StubToolProvidingIntegration(BaseToolProvidingIntegration):
    TYPE = "stub"
    NAME = "Stub"

    def __init__(self, tools=None, error=None):
        self._stub_tools = tools or []
        self._error = error

    async def get_tools(self):
        if self._error:
            raise self._error
        return self._stub_tools


class TestAgentBuilderBuildDynamicTools:
    def _make_builder(self, resolver_cls):
        config = MagicMock()
        config.integration_plugin_resolver = resolver_cls
        builder = AgentBuilder(config=config, conversation_id=1)
        builder._data_set_id = 42
        return builder

    def test_returns_empty_list_when_no_resolver_configured(self):
        builder = self._make_builder(resolver_cls=None)

        tools = asyncio.run(builder._build_dynamic_tools())

        assert tools == []

    def test_merges_tools_from_every_reachable_integration(self):
        resolver_instance = MagicMock()
        resolver_instance.resolve_all.return_value = [
            StubToolProvidingIntegration(tools=["a", "b"]),
            StubToolProvidingIntegration(tools=["c"]),
        ]
        builder = self._make_builder(resolver_cls=MagicMock(return_value=resolver_instance))

        tools = asyncio.run(builder._build_dynamic_tools())

        assert tools == ["a", "b", "c"]

    def test_one_unreachable_integration_does_not_block_the_others(self):
        resolver_instance = MagicMock()
        resolver_instance.resolve_all.return_value = [
            StubToolProvidingIntegration(error=ConnectionError("server down")),
            StubToolProvidingIntegration(tools=["still_works"]),
        ]
        builder = self._make_builder(resolver_cls=MagicMock(return_value=resolver_instance))

        tools = asyncio.run(builder._build_dynamic_tools())

        assert tools == ["still_works"]
