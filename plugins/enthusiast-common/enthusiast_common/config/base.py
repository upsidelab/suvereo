from __future__ import annotations

from typing import Generic, Optional, Type, TypeVar

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.chat_history import BaseChatMessageHistory
from pydantic import BaseModel, ConfigDict

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
    registry_class: Type[BaseEmbeddingProviderRegistry]
    providers: Optional[dict[str, str]] = None


class LLMRegistryConfig(ArbitraryTypeBaseModel):
    registry_class: Type[BaseLanguageModelRegistry]
    providers: Optional[dict[str, str]] = None


class ModelsRegistryConfig(ArbitraryTypeBaseModel):
    registry_class: Type[BaseDBModelsRegistry]
    models_config: Optional[dict[str, str]] = None


class RegistryConfig(ArbitraryTypeBaseModel):
    llm: LLMRegistryConfig
    embeddings: EmbeddingsRegistryConfig
    model: ModelsRegistryConfig


class CallbackHandlerConfig(ArbitraryTypeBaseModel):
    handler_class: Type[BaseCallbackHandler]


class LLMConfig(ArbitraryTypeBaseModel):
    llm_class: Type[BaseLLM] = BaseLLM
    callbacks: Optional[list[CallbackHandlerConfig]] = None


class RepositoriesConfig(ArbitraryTypeBaseModel):
    user: Type[BaseUserRepository]
    message: Type[BaseMessageRepository]
    conversation: Type[BaseConversationRepository]
    data_set: Type[BaseDataSetRepository]
    agent: Type[BaseAgentRepository]


class FunctionToolConfig(ArbitraryTypeBaseModel):
    tool_class: Type[BaseFunctionTool]


class LLMToolConfig(ArbitraryTypeBaseModel):
    tool_class: Type[BaseLLMTool]
    llm: Optional[LLMConfig] = None


class FileToolConfig(ArbitraryTypeBaseModel):
    tool_class: Type[BaseFileTool]
    llm: Optional[LLMConfig] = None


class AgentToolConfig(ArbitraryTypeBaseModel):
    tool_class: Type[BaseAgentTool]
    agent: AgentConfig


class AgentCallbackHandlerConfig(ArbitraryTypeBaseModel):
    handler_class: Type[BaseCallbackHandler]


class MemoryConfig(ArbitraryTypeBaseModel):
    """Conversation memory classes the host provides for agent building.

    ``chat_history_class`` is constructed as ``(conversation_repo, conversation_id)``;
    ``compactor_class`` as ``(conversation_repo, conversation_id, llm, chat_history)``.
    """

    chat_history_class: Type[BaseChatMessageHistory]
    compactor_class: Optional[Type[BaseMemoryCompactor]] = None


class AgentConfig(ArbitraryTypeBaseModel, Generic[InjectorT]):
    agent_class: Type[BaseAgent]
    llm: LLMConfig
    repositories: RepositoriesConfig
    injector: Type[InjectorT]
    registry: RegistryConfig
    system_prompt: str
    memory: MemoryConfig
    tools: Optional[list[FunctionToolConfig | LLMToolConfig | AgentToolConfig | FileToolConfig]] = None
    agent_callback_handler: Optional[AgentCallbackHandlerConfig] = None
    memory_compactor_enabled: bool = False
    similarity_searcher: Optional[Type[BaseSimilaritySearcher]] = None
    integration_plugin_resolver: Optional[Type[BaseIntegrationPluginResolver]] = None


class AgentConfigWithDefaults(AgentConfig, Generic[InjectorT]):
    system_prompt: Optional[str] = None
    repositories: Optional[RepositoriesConfig] = None
    injector: Optional[Type[InjectorT]] = None
    registry: Optional[RegistryConfig] = None
    llm: Optional[LLMConfig] = None
    memory: Optional[MemoryConfig] = None
