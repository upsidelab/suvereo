from typing import Optional, Type

from django.conf import settings
from enthusiast_common.config import (
    AgentCallbackHandlerConfig,
    AgentConfig,
    AgentConfigWithDefaults,
    EmbeddingsRegistryConfig,
    LLMConfig,
    LLMRegistryConfig,
    MemoryConfig,
    ModelsRegistryConfig,
    RegistryConfig,
    RepositoriesConfig,
)
from enthusiast_common.injectors import Injector
from enthusiast_common.integrations import BaseIntegrationPluginResolver
from enthusiast_common.retrievers import BaseSimilaritySearcher
from pydantic import BaseModel

from agent.core.callbacks import ConversationWebSocketCallbackHandler
from agent.core.memory import LLMMemoryCompactor, PersistentChatHistory
from agent.core.registries.embeddings import EmbeddingProviderRegistry
from agent.core.registries.language_models import LanguageModelRegistry
from agent.core.registries.models import BaseDjangoSettingsDBModelRegistry
from agent.core.repositories import (
    DjangoAgentRepository,
    DjangoConversationRepository,
    DjangoDataSetRepository,
    DjangoMessageRepository,
    DjangoUserRepository,
)
from catalog.integrations.resolver import IntegrationPluginResolver
from catalog.retrieval.searcher import EmbeddingSimilaritySearcher


class DefaultAgentConfig(BaseModel):
    repositories: RepositoriesConfig
    injector: Type[Injector]
    registry: RegistryConfig
    llm: LLMConfig
    memory: MemoryConfig
    conversation_history_token_limit: int
    agent_callback_handler: Optional[AgentCallbackHandlerConfig] = None
    similarity_searcher: Optional[Type[BaseSimilaritySearcher]] = None
    integration_plugin_resolver: Optional[Type[BaseIntegrationPluginResolver]] = None


def get_default_config() -> DefaultAgentConfig:
    return DefaultAgentConfig(
        repositories=RepositoriesConfig(
            user=DjangoUserRepository,
            data_set=DjangoDataSetRepository,
            conversation=DjangoConversationRepository,
            message=DjangoMessageRepository,
            agent=DjangoAgentRepository,
        ),
        injector=Injector,
        registry=RegistryConfig(
            llm=LLMRegistryConfig(registry_class=LanguageModelRegistry),
            embeddings=EmbeddingsRegistryConfig(registry_class=EmbeddingProviderRegistry),
            model=ModelsRegistryConfig(registry_class=BaseDjangoSettingsDBModelRegistry),
        ),
        llm=LLMConfig(),
        memory=MemoryConfig(
            chat_history_class=PersistentChatHistory,
            compactor_class=LLMMemoryCompactor,
        ),
        conversation_history_token_limit=settings.DEFAULT_CONVERSATION_HISTORY_TOKEN_LIMIT,
        agent_callback_handler=AgentCallbackHandlerConfig(handler_class=ConversationWebSocketCallbackHandler),
        similarity_searcher=EmbeddingSimilaritySearcher,
        integration_plugin_resolver=IntegrationPluginResolver,
    )


def merge_config(
    partial: AgentConfigWithDefaults,
) -> AgentConfig:
    merged: dict[str, object] = {}
    defaults = get_default_config()
    for name in AgentConfig.model_fields:
        value = getattr(partial, name, None)

        if value is not None:
            merged[name] = value
        else:
            merged[name] = getattr(defaults, name, None)

    return AgentConfig(**merged)
