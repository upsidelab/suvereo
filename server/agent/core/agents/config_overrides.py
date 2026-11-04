from typing import Any

from suvereo_common.config import (
    AgentCallbackHandlerConfig,
    AgentConfig,
    CallbackHandlerConfig,
    RepositoriesConfig,
    ToolConfig,
)
from suvereo_common.config.base import ArbitraryTypeBaseModel
from suvereo_common.integrations import BaseIntegrationPluginResolver
from suvereo_common.llm import BaseLLM
from suvereo_common.utils import deep_merge


class AgentConfigOverrides(ArbitraryTypeBaseModel):
    """Per-build changes to an agent's merged config; unset fields keep the config's values."""

    llm_class: type[BaseLLM] | None = None
    llm_callbacks: list[CallbackHandlerConfig] | None = None
    agent_callback_handler: AgentCallbackHandlerConfig | None = None
    integration_plugin_resolver: type[BaseIntegrationPluginResolver] | None = None
    repositories: RepositoriesConfig | None = None
    system_prompt: str | None = None
    tools: list[ToolConfig] | None = None
    agent_config_patch: dict[str, Any] | None = None

    def with_fallback(self, base: "AgentConfigOverrides") -> "AgentConfigOverrides":
        """A copy where every field these overrides leave unset takes the value from ``base``."""
        return self.model_copy(
            update={name: getattr(base, name) for name in type(self).model_fields if getattr(self, name) is None}
        )

    def apply(self, config: AgentConfig) -> AgentConfig:
        """A copy of the config with these overrides applied; LLM callbacks are added, the rest replaced."""
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
        if self.repositories is not None:
            update["repositories"] = self.repositories
        if self.system_prompt is not None:
            update["system_prompt"] = self.system_prompt
        if self.tools is not None:
            update["tools"] = self.tools
        if self.agent_config_patch:
            update["runtime_arguments_patch"] = deep_merge(
                config.runtime_arguments_patch or {}, self.agent_config_patch
            )
        return config.model_copy(update=update)
