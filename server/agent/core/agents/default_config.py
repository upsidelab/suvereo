from typing import Optional, Type

from enthusiast_common.config import (
    AgentCallbackHandlerConfig,
    AgentConfig,
    AgentConfigWithDefaults,
    EmbeddingsRegistryConfig,
    LLMConfig,
    LLMRegistryConfig,
    ModelsRegistryConfig,
    RegistryConfig,
    RepositoriesConfig,
)
from enthusiast_common.retrievers import BaseSimilaritySearcher
from pydantic import BaseModel

from agent.core.callbacks import ConversationWebSocketCallbackHandler
from agent.core.injector import Injector
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
from catalog.retrieval.searcher import EmbeddingSimilaritySearcher


class DefaultAgentConfig(BaseModel):
    repositories: RepositoriesConfig
    injector: Type[Injector]
    registry: RegistryConfig
    llm: LLMConfig
    agent_callback_handler: Optional[AgentCallbackHandlerConfig] = None
    similarity_searcher: Optional[Type[BaseSimilaritySearcher]] = None


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
        agent_callback_handler=AgentCallbackHandlerConfig(handler_class=ConversationWebSocketCallbackHandler),
        similarity_searcher=EmbeddingSimilaritySearcher,
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
