from __future__ import annotations

from typing import Any, Generic, TypeVar

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.chat_history import BaseChatMessageHistory
from pydantic import BaseModel, ConfigDict, Field

from ..agents import BaseAgent
from ..injectors.base import BaseInjector
from ..integrations.base import BaseIntegrationPluginResolver
from ..llm import BaseLLM
from ..memory import BaseMemoryCompactor
from ..registry import (
    BaseDBModelsRegistry,
    BaseEmbeddingProviderRegistry,
    BaseLanguageModelRegistry,
)
from ..repositories.base import (
    BaseAgentRepository,
    BaseConversationRepository,
    BaseDataSetRepository,
    BaseMessageRepository,
    BaseUserRepository,
)
from ..retrievers import BaseSimilaritySearcher
from ..tools import BaseAgentTool, BaseFileTool, BaseFunctionTool, BaseLLMTool

InjectorT = TypeVar("InjectorT", bound=BaseInjector)


class ArbitraryTypeBaseModel(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)


class EmbeddingsRegistryConfig(ArbitraryTypeBaseModel):
    registry_class: type[BaseEmbeddingProviderRegistry]
    providers: dict[str, str] | None = None


class LLMRegistryConfig(ArbitraryTypeBaseModel):
    registry_class: type[BaseLanguageModelRegistry]
    providers: dict[str, str] | None = None


class ModelsRegistryConfig(ArbitraryTypeBaseModel):
    registry_class: type[BaseDBModelsRegistry]
    models_config: dict[str, str] | None = None


class RegistryConfig(ArbitraryTypeBaseModel):
    llm: LLMRegistryConfig
    embeddings: EmbeddingsRegistryConfig
    model: ModelsRegistryConfig


class CallbackHandlerConfig(ArbitraryTypeBaseModel):
    handler_class: type[BaseCallbackHandler]


class LLMConfig(ArbitraryTypeBaseModel):
    llm_class: type[BaseLLM] = BaseLLM
    callbacks: list[CallbackHandlerConfig] | None = None


class RepositoriesConfig(ArbitraryTypeBaseModel):
    user: type[BaseUserRepository]
    message: type[BaseMessageRepository]
    conversation: type[BaseConversationRepository]
    data_set: type[BaseDataSetRepository]
    agent: type[BaseAgentRepository]


class FunctionToolConfig(ArbitraryTypeBaseModel):
    tool_class: type[BaseFunctionTool]


class LLMToolConfig(ArbitraryTypeBaseModel):
    tool_class: type[BaseLLMTool]
    llm: LLMConfig | None = None


class FileToolConfig(ArbitraryTypeBaseModel):
    tool_class: type[BaseFileTool]
    llm: LLMConfig | None = None


class AgentToolConfig(ArbitraryTypeBaseModel):
    tool_class: type[BaseAgentTool]
    agent_class: type[BaseAgent]


ToolConfig = FunctionToolConfig | LLMToolConfig | AgentToolConfig | FileToolConfig


class AgentCallbackHandlerConfig(ArbitraryTypeBaseModel):
    handler_class: type[BaseCallbackHandler]


class MemoryConfig(ArbitraryTypeBaseModel):
    """Conversation memory classes the host provides for agent building.

    ``chat_history_class`` is constructed as ``(conversation_repo, conversation_id)``;
    ``compactor_class`` as ``(conversation_repo, conversation_id, llm, chat_history)``.
    """

    chat_history_class: type[BaseChatMessageHistory]
    compactor_class: type[BaseMemoryCompactor] | None = None


class AgentConfig(ArbitraryTypeBaseModel, Generic[InjectorT]):
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
    repositories: RepositoriesConfig | None = None
    injector: type[InjectorT] | None = None
    registry: RegistryConfig | None = None
    llm: LLMConfig | None = None
    memory: MemoryConfig | None = None
    conversation_history_token_limit: int | None = Field(default=None, gt=0)
