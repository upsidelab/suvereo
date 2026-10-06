from typing import Any

from enthusiast_common.config import AgentCallbackHandlerConfig, AgentConfig, CallbackHandlerConfig
from enthusiast_common.config.base import ArbitraryTypeBaseModel
from enthusiast_common.integrations import BaseIntegrationPluginResolver
from enthusiast_common.llm import BaseLLM
from enthusiast_common.utils import deep_merge


class AgentConfigOverrides(ArbitraryTypeBaseModel):
    """Per-build changes to an agent's merged config; unset fields keep the config's values."""

    llm_class: type[BaseLLM] | None = None
    llm_callbacks: list[CallbackHandlerConfig] | None = None
    agent_callback_handler: AgentCallbackHandlerConfig | None = None
    integration_plugin_resolver: type[BaseIntegrationPluginResolver] | None = None
    system_prompt: str | None = None
    agent_config_patch: dict[str, Any] | None = None

    def apply(self, config: AgentConfig) -> AgentConfig:
        """Apply these overrides to an agent's merged config.

        Args:
            config: The merged config to start from; it is not modified.

        Returns:
            A copy with LLM callbacks added and every other set field replaced.
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
