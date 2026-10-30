import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agent.core.registries.agents.agent_registry import AgentRegistry


class TestAgentRegistryIntegrationTools:
    @pytest.mark.parametrize(("integration_tools", "built_with_abuild"), [(False, False), (True, True)])
    def test_aget_conversation_agent_attaches_integration_tools_only_when_agent_opted_in(
        self, integration_tools, built_with_abuild
    ):
        conversation = MagicMock()
        conversation.agent.integration_tools = integration_tools
        builder = MagicMock()
        builder.abuild = AsyncMock(return_value="abuilt")
        builder.build.return_value = "built"

        with patch.object(AgentRegistry, "_build_agent_builder", return_value=builder):
            agent = asyncio.run(AgentRegistry().aget_conversation_agent(conversation, streaming=False))

        assert agent == ("abuilt" if built_with_abuild else "built")
        assert builder.abuild.await_count == int(built_with_abuild)
