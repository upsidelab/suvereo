from typing import Any, Optional, Type

from enthusiast_common.config import AgentCallbackHandlerConfig, AgentConfig, CallbackHandlerConfig
from enthusiast_common.config.base import ArbitraryTypeBaseModel
from enthusiast_common.integrations import BaseIntegrationPluginResolver
from enthusiast_common.llm import BaseLLM
from enthusiast_common.utils import deep_merge


class AgentConfigOverrides(ArbitraryTypeBaseModel):
    """Per-build changes to an agent's merged config, leaving the plugin and the stored agent untouched.

    Every field is optional; an unset field keeps whatever the config already has.

    Attributes:
        llm_class: Replaces the ``BaseLLM`` used for every LLM the agent builds, e.g. to pin a model.
        llm_callbacks: Added to the configured LLM callbacks, so they see every LLM call, nested ones included.
        agent_callback_handler: Replaces the agent's callback handler.
        integration_plugin_resolver: Replaces how the agent finds its integrations.
        system_prompt: Replaces the system prompt.
        agent_config_patch: Deep-merged over the agent's stored config (its runtime arguments).
    """

    llm_class: Optional[Type[BaseLLM]] = None
    llm_callbacks: Optional[list[CallbackHandlerConfig]] = None
    agent_callback_handler: Optional[AgentCallbackHandlerConfig] = None
    integration_plugin_resolver: Optional[Type[BaseIntegrationPluginResolver]] = None
    system_prompt: Optional[str] = None
    agent_config_patch: Optional[dict[str, Any]] = None

    def apply(self, config: AgentConfig) -> AgentConfig:
        """Return a copy of ``config`` with these overrides applied.

        Args:
            config: The agent's merged config.

        Returns:
            A new config; ``config`` itself is not modified.
        """
        llm_update: dict[str, Any] = {}
        if self.llm_class is not None:
            llm_update["llm_class"] = self.llm_class
        if self.llm_callbacks:
            llm_update["callbacks"] = [*(config.llm.callbacks or []), *self.llm_callbacks]

        update: dict[str, Any] = {}
        if llm_update:
            update["llm"] = config.llm.model_copy(update=llm_update)
        if self.agent_callback_handler is not None:
            update["agent_callback_handler"] = self.agent_callback_handler
        if self.integration_plugin_resolver is not None:
            update["integration_plugin_resolver"] = self.integration_plugin_resolver
        if self.system_prompt is not None:
            update["system_prompt"] = self.system_prompt
        if self.agent_config_patch:
            update["runtime_arguments_patch"] = deep_merge(
                config.runtime_arguments_patch or {}, self.agent_config_patch
            )
        return config.model_copy(update=update)
