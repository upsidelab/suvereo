from unittest.mock import MagicMock, patch

import pytest
from enthusiast_common.agents import BaseAgent
from enthusiast_common.config import AgentCallbackHandlerConfig, AgentConfigWithDefaults, CallbackHandlerConfig
from enthusiast_common.integrations import BaseIntegrationPluginResolver
from enthusiast_common.llm import BaseLLM
from langchain_core.callbacks import BaseCallbackHandler

from agent.core.agents.config_overrides import AgentConfigOverrides
from agent.core.agents.default_config import merge_config
from agent.core.registries.agents.agent_registry import AgentRegistry


class StubAgent(BaseAgent):
    SYSTEM_PROMPT = "original prompt"

    def get_answer(self, input_text: str) -> str:
        return ""


class ConfiguredHandler(BaseCallbackHandler):
    pass


class AddedHandler(BaseCallbackHandler):
    pass


class PinnedLLM(BaseLLM):
    pass


class StubResolver(BaseIntegrationPluginResolver):
    def resolve(self, data_set_id, plugin_base):
        return None


@pytest.fixture
def config():
    merged = merge_config(AgentConfigWithDefaults(system_prompt="original prompt"))
    return merged.model_copy(
        update={
            "llm": merged.llm.model_copy(update={"callbacks": [CallbackHandlerConfig(handler_class=ConfiguredHandler)]})
        }
    )


class TestAgentConfigOverrides:
    def test_apply_without_overrides_keeps_the_config(self, config):
        applied = AgentConfigOverrides().apply(config)

        assert applied.model_dump() == config.model_dump()

    def test_apply_does_not_modify_the_original(self, config):
        AgentConfigOverrides(system_prompt="new", llm_class=PinnedLLM).apply(config)

        assert config.system_prompt == "original prompt"
        assert config.llm.llm_class is BaseLLM

    def test_apply_replaces_the_llm_class(self, config):
        assert AgentConfigOverrides(llm_class=PinnedLLM).apply(config).llm.llm_class is PinnedLLM

    def test_apply_adds_llm_callbacks_after_the_configured_ones(self, config):
        overrides = AgentConfigOverrides(llm_callbacks=[CallbackHandlerConfig(handler_class=AddedHandler)])

        callbacks = overrides.apply(config).llm.callbacks

        assert [c.handler_class for c in callbacks] == [ConfiguredHandler, AddedHandler]

    def test_apply_replaces_the_agent_callback_handler(self, config):
        handler = AgentCallbackHandlerConfig(handler_class=AddedHandler)

        assert AgentConfigOverrides(agent_callback_handler=handler).apply(config).agent_callback_handler == handler

    def test_apply_replaces_the_integration_plugin_resolver(self, config):
        applied = AgentConfigOverrides(integration_plugin_resolver=StubResolver).apply(config)

        assert applied.integration_plugin_resolver is StubResolver

    def test_apply_replaces_the_system_prompt(self, config):
        assert AgentConfigOverrides(system_prompt="variant prompt").apply(config).system_prompt == "variant prompt"

    def test_apply_sets_the_agent_config_patch(self, config):
        patch_ = {"prompt_input": {"tone": "formal"}}

        assert AgentConfigOverrides(agent_config_patch=patch_).apply(config).runtime_arguments_patch == patch_


class TestAgentRegistryAppliesOverrides:
    def test_get_conversation_agent_builds_with_the_overridden_config(self, config):
        conversation = MagicMock(id=1)
        with (
            patch.object(AgentRegistry, "get_agent_class_by_type", return_value=StubAgent),
            patch("agent.core.registries.agents.agent_registry.AgentBuilder") as builder,
        ):
            AgentRegistry().get_conversation_agent(
                conversation, streaming=False, overrides=AgentConfigOverrides(system_prompt="variant prompt")
            )

        assert builder.call_args.kwargs["config"].system_prompt == "variant prompt"
