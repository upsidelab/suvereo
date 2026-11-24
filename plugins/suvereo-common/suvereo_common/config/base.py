from __future__ import annotations

from typing import Any, Generic, TypeVar

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.chat_history import BaseChatMessageHistory
from pydantic import BaseModel, ConfigDict, Field
from suvereo_common.agents import BaseAgent
from suvereo_common.injectors.base import BaseInjector
from suvereo_common.integrations.base import BaseIntegrationPluginResolver
from suvereo_common.llm import BaseLLM
from suvereo_common.memory import BaseMemoryCompactor
from suvereo_common.registry import (
    BaseDBModelsRegistry,
    BaseEmbeddingProviderRegistry,
    BaseLanguageModelRegistry,
)
from suvereo_common.repositories.base import (
    BaseAgentRepository,
    BaseConversationRepository,
    BaseDataSetRepository,
    BaseMessageRepository,
    BaseUserRepository,
)
from suvereo_common.retrievers import BaseSimilaritySearcher
from suvereo_common.tools import BaseAgentTool, BaseFileTool, BaseFunctionTool, BaseLLMTool

InjectorT = TypeVar("InjectorT", bound=BaseInjector)


class ArbitraryTypeBaseModel(BaseModel):
    """A config model that accepts classes and other arbitrary types as values."""

    model_config = ConfigDict(arbitrary_types_allowed=True)


class EmbeddingsRegistryConfig(ArbitraryTypeBaseModel):
    """The embedding provider registry to use."""

    registry_class: type[BaseEmbeddingProviderRegistry]
    providers: dict[str, str] | None = None


class LLMRegistryConfig(ArbitraryTypeBaseModel):
    """The language model registry to use."""

    registry_class: type[BaseLanguageModelRegistry]
    providers: dict[str, str] | None = None


class ModelsRegistryConfig(ArbitraryTypeBaseModel):
    """The database model registry to use."""

    registry_class: type[BaseDBModelsRegistry]
    models_config: dict[str, str] | None = None


class RegistryConfig(ArbitraryTypeBaseModel):
    """The registries an agent is built with."""

    llm: LLMRegistryConfig
    embeddings: EmbeddingsRegistryConfig
    model: ModelsRegistryConfig


class CallbackHandlerConfig(ArbitraryTypeBaseModel):
    """A callback handler class to attach to the language model."""

    handler_class: type[BaseCallbackHandler]


class LLMConfig(ArbitraryTypeBaseModel):
    """The language model wrapper and its callback handlers."""

    llm_class: type[BaseLLM] = BaseLLM
    callbacks: list[CallbackHandlerConfig] | None = None


class RepositoriesConfig(ArbitraryTypeBaseModel):
    """The repository classes an agent reads data through."""

    user: type[BaseUserRepository]
    message: type[BaseMessageRepository]
    conversation: type[BaseConversationRepository]
    data_set: type[BaseDataSetRepository]
    agent: type[BaseAgentRepository]


class FunctionToolConfig(ArbitraryTypeBaseModel):
    """A tool that needs no language model or injector."""

    tool_class: type[BaseFunctionTool]


class LLMToolConfig(ArbitraryTypeBaseModel):
    """A tool that uses the language model and the injector."""

    tool_class: type[BaseLLMTool]
    llm: LLMConfig | None = None


class FileToolConfig(ArbitraryTypeBaseModel):
    """A tool that works with files attached to the conversation."""

    tool_class: type[BaseFileTool]
    llm: LLMConfig | None = None


class AgentToolConfig(ArbitraryTypeBaseModel):
    """A tool that calls another agent."""

    tool_class: type[BaseAgentTool]
    agent_class: type[BaseAgent]


ToolConfig = FunctionToolConfig | LLMToolConfig | AgentToolConfig | FileToolConfig


class AgentCallbackHandlerConfig(ArbitraryTypeBaseModel):
    """A callback handler class to attach to the agent."""

    handler_class: type[BaseCallbackHandler]


class MemoryConfig(ArbitraryTypeBaseModel):
    """Conversation memory classes the host provides for agent building.

    ``chat_history_class`` is constructed as ``(conversation_repo, conversation_id)``;
    ``compactor_class`` as ``(conversation_repo, conversation_id, llm, chat_history)``.
    """

    chat_history_class: type[BaseChatMessageHistory]
    compactor_class: type[BaseMemoryCompactor] | None = None


class AgentConfig(ArbitraryTypeBaseModel, Generic[InjectorT]):
    """Everything needed to build an agent."""

    llm: LLMConfig
    repositories: RepositoriesConfig
    injector: type[InjectorT]
    registry: RegistryConfig
    system_prompt: str
    memory: MemoryConfig
    tools: list[ToolConfig] | None = None
    agent_callback_handler: AgentCallbackHandlerConfig | None = None
    conversation_history_token_limit: int = Field(gt=0)
    memory_compactor_enabled: bool = False
    similarity_searcher: type[BaseSimilaritySearcher] | None = None
    integration_plugin_resolver: type[BaseIntegrationPluginResolver] | None = None
    runtime_arguments_patch: dict[str, Any] | None = None


class AgentConfigWithDefaults(AgentConfig, Generic[InjectorT]):
    """An agent config whose missing parts fall back to the host's defaults."""

    repositories: RepositoriesConfig | None = None
    injector: type[InjectorT] | None = None
    registry: RegistryConfig | None = None
    llm: LLMConfig | None = None
    memory: MemoryConfig | None = None
    conversation_history_token_limit: int | None = Field(default=None, gt=0)
