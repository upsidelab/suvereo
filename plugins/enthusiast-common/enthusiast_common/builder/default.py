import asyncio
import logging
from typing import Optional, Type

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.language_models import BaseLanguageModel
from langchain_core.tools import BaseTool

from ..agents import BaseAgent
from ..callbacks import ConversationCallbackHandler
from ..config.base import (
    AgentConfig,
    AgentToolConfig,
    FileToolConfig,
    FunctionToolConfig,
    LLMConfig,
    LLMToolConfig,
)
from ..injectors import BaseInjector
from ..integrations import BaseToolProvidingIntegration
from ..memory import BaseMemoryCompactor
from ..registry import BaseDBModelsRegistry, BaseEmbeddingProviderRegistry, BaseLanguageModelRegistry
from ..structures import RepositoriesInstances
from ..tools import BaseAgentTool, BaseFileTool, BaseFunctionTool, BaseLLMTool
from ..utils import deep_merge, run_off_event_loop
from .base import BaseAgentBuilder, ConfigT

logger = logging.getLogger(__name__)

#: How long a single tool-providing integration gets to answer before it is skipped for this turn.
#: Kept well under a conversational attention span: the user is waiting on the reply this blocks.
DYNAMIC_TOOL_FETCH_TIMEOUT_SECONDS = 10


class AgentBuilder(BaseAgentBuilder[ConfigT]):
    """Default, config-driven implementation of :class:`BaseAgentBuilder`.

    The whole build is driven by the ``AgentConfig``: every host-specific piece
    (repositories, registries, memory classes, callback handlers, the
    integration plugin resolver) arrives through the config, so this class
    depends only on contracts defined in ``enthusiast-common``. The framework
    host supplies its implementations via its default config; a vertical
    subclasses this builder only to extend the injector with domain-specific
    dependencies.
    """

    _repositories: RepositoriesInstances

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._llm_registry = None
        self._llm = None
        self._default_llm = None
        self._embeddings_registry = None
        self._data_set_id = None
        self._injector = None

    def build(self) -> BaseAgent:
        """Build the agent: repositories, registries, LLMs, injector, tools, callbacks."""
        model_registry = self._build_db_models_registry()
        self._build_and_set_repositories(model_registry)
        self._data_set_id = self._repositories.conversation.get_data_set_id(self.conversation_id)
        self._llm_registry = self._build_llm_registry()
        self._embeddings_registry = self._build_embeddings_registry()
        self._llm = self._build_llm(self._config.llm)
        self._default_llm = self._build_default_llm()
        self._injector = self._build_injector()
        tools = self._build_tools(default_llm=self._default_llm, injector=self._injector)
        agent_callback_handler = self._build_agent_callback_handler()
        agent_instance = self._build_agent(tools, self._llm, agent_callback_handler)
        self._inject_additional_arguments(agent_instance)
        return agent_instance

    async def abuild(self) -> BaseAgent:
        """Async twin of build(): also attaches this dataset's tool-providing integrations' tools.

        Runs the existing synchronous build() in a worker thread so ORM calls inside it don't hit
        a "sync call from an async context" guard — that guard only fires when a sync DB call
        happens on a thread that already has a running event loop, and a plain worker thread has
        none. Callers reach for this only once they know the data set has tools worth fetching,
        so the fetch is unconditional here.
        """
        agent_instance = await run_off_event_loop(self.build)
        agent_instance.set_dynamic_tools(await self._build_dynamic_tools())
        return agent_instance

    async def _build_dynamic_tools(self) -> list[BaseTool]:
        """Fetch tools from every tool-providing integration configured on this dataset.

        The fetches run concurrently and each is capped by its own timeout, because this sits on the
        critical path of a conversation turn: served sequentially, a handful of unresponsive servers
        would add up to minutes of silence before the user saw any answer. An integration that fails
        or times out contributes no tools and is logged, leaving the healthy ones unaffected.
        """
        resolver_cls = self._config.integration_plugin_resolver
        if resolver_cls is None:
            return []
        integrations = await run_off_event_loop(
            resolver_cls().resolve_all, self._data_set_id, BaseToolProvidingIntegration
        )
        if not integrations:
            return []
        fetched = await asyncio.gather(*(self._fetch_integration_tools(i) for i in integrations))
        return [tool for tools in fetched for tool in tools]

    async def _fetch_integration_tools(self, integration: BaseToolProvidingIntegration) -> list[BaseTool]:
        """Fetch one integration's tools, returning none if it cannot answer in time."""
        try:
            tools = await asyncio.wait_for(integration.get_tools(), timeout=DYNAMIC_TOOL_FETCH_TIMEOUT_SECONDS)
        except TimeoutError:
            logger.warning(
                "Timed out after %ss fetching tools from %s integration (dataset %s)",
                DYNAMIC_TOOL_FETCH_TIMEOUT_SECONDS,
                integration.TYPE,
                self._data_set_id,
            )
            return []
        except Exception:
            logger.warning(
                "Failed to fetch tools from %s integration (dataset %s)",
                integration.TYPE,
                self._data_set_id,
                exc_info=True,
            )
            return []
        logger.info(
            "Fetched %s tool(s) from %s integration (dataset %s): %s",
            len(tools),
            integration.TYPE,
            self._data_set_id,
            ", ".join(tool.name for tool in tools) or "none",
        )
        return tools

    def _inject_additional_arguments(self, agent_instance: BaseAgent) -> None:
        agent_instance.set_runtime_arguments(self._agent_runtime_arguments())

    def _agent_runtime_arguments(self) -> dict:
        """The agent's stored runtime arguments, with the config's ``runtime_arguments_patch`` merged in."""
        agent_configuration_id = self._repositories.conversation.get_agent_id(self.conversation_id)
        runtime_arguments = self._repositories.agent.get_agent_configuration_by_id(agent_configuration_id)
        if patch := self._config.runtime_arguments_patch:
            return deep_merge(runtime_arguments, patch)
        return runtime_arguments

    def _build_agent(
        self,
        tools: list[BaseTool],
        llm: BaseLanguageModel,
        callback_handler: BaseCallbackHandler,
    ) -> BaseAgent:
        return self._agent_class(
            tools=tools,
            llm=llm,
            system_prompt=self._config.system_prompt,
            conversation_id=self.conversation_id,
            callback_handler=callback_handler,
            injector=self._injector,
            conversation_history_token_limit=self._config.conversation_history_token_limit,
        )

    def _build_llm_registry(self) -> BaseLanguageModelRegistry:
        llm_registry_class = self._config.registry.llm.registry_class
        if providers := self._config.registry.llm.providers:
            return llm_registry_class(providers=providers)
        return llm_registry_class(data_set_repo=self._repositories.data_set)

    def _build_db_models_registry(self) -> BaseDBModelsRegistry:
        db_models_registry_class = self._config.registry.model.registry_class
        if models_config := self._config.registry.model.models_config:
            return db_models_registry_class(models_config=models_config)
        return db_models_registry_class()

    def _build_and_set_repositories(self, models_registry: BaseDBModelsRegistry) -> None:
        repositories = {}
        for name in self._config.repositories.__class__.model_fields.keys():
            repo_class = getattr(self._config.repositories, name)
            model_class = models_registry.get_model_class_by_name(name)
            repositories[name] = repo_class(model_class)
        self._repositories = RepositoriesInstances(**repositories)

    def _build_embeddings_registry(self) -> BaseEmbeddingProviderRegistry:
        embeddings_registry_class = self._config.registry.embeddings.registry_class
        if providers := self._config.registry.embeddings.providers:
            return embeddings_registry_class(providers=providers)
        return embeddings_registry_class(data_set_repo=self._repositories.data_set)

    def _build_llm(self, llm_config: LLMConfig) -> BaseLanguageModel:
        callbacks = self._build_llm_callback_handlers()
        llm = llm_config.llm_class(
            llm_registry=self._llm_registry,
            callbacks=callbacks,
            streaming=self.streaming,
            data_set_repo=self._repositories.data_set,
        )
        return llm.create(self._data_set_id)

    def _build_default_llm(self) -> BaseLanguageModel:
        """The non-streaming LLM used by tools, retrievers and the memory compactor, with the same callbacks."""
        llm = self._config.llm.llm_class(
            llm_registry=self._build_llm_registry(),
            callbacks=self._build_llm_callback_handlers(),
            data_set_repo=self._repositories.data_set,
        )
        return llm.create(self._data_set_id)

    def _build_tools(self, default_llm: BaseLanguageModel, injector: BaseInjector) -> list[BaseTool]:
        tools = []

        for tool_config in self._config.tools:
            if isinstance(tool_config, FunctionToolConfig):
                tools.append(self._build_function_tool(config=tool_config))
            elif isinstance(tool_config, LLMToolConfig):
                tools.append(self._build_llm_tool(config=tool_config, injector=injector, default_llm=default_llm))
            elif isinstance(tool_config, AgentToolConfig):
                tools.append(self._build_agent_tool(config=tool_config))
            elif isinstance(tool_config, FileToolConfig):
                tools.append(self._build_file_tool(config=tool_config, injector=injector, default_llm=default_llm))
            else:
                continue
        return tools

    def _build_function_tool(self, config: FunctionToolConfig) -> BaseFunctionTool:
        return config.tool_class()

    def _build_llm_tool(
        self, config: LLMToolConfig, default_llm: BaseLanguageModel, injector: BaseInjector
    ) -> BaseLLMTool:
        llm = default_llm
        if config.llm:
            llm = config.llm
        return config.tool_class(
            data_set_id=self._data_set_id,
            llm=llm,
            injector=injector,
        )

    def _build_file_tool(
        self, config: FileToolConfig, default_llm: BaseLanguageModel, injector: BaseInjector
    ) -> BaseFileTool:
        llm = default_llm
        if config.llm:
            llm = config.llm
        return config.tool_class(
            data_set_id=self._data_set_id,
            conversation_id=self.conversation_id,
            llm_registry=self._llm_registry,
            llm=llm,
            injector=injector,
        )

    def _build_agent_tool(self, config: AgentToolConfig) -> BaseAgentTool:
        # Sub-agents are built with the same builder class as their parent, so a
        # vertical builder propagates its injector (and its build costs) to
        # sub-agents — overriding whatever config.agent.injector declares.
        agent = type(self)(
            config.agent_class,
            self._sub_agent_config(config.agent_class),
            self.conversation_id,
            self.streaming,
        ).build()
        return config.tool_class(agent=agent)

    def _sub_agent_config(self, agent_class: Type[BaseAgent]) -> AgentConfig:
        """The sub-agent's own config laid over this agent's resolved one; fields it leaves unset are inherited."""
        own = agent_class.get_config()
        update = {name: value for name in AgentConfig.model_fields if (value := getattr(own, name, None)) is not None}
        return self._config.model_copy(update=update)

    def _build_injector(self) -> BaseInjector:
        chat_history = self._build_chat_history()
        memory_compactor = self._build_memory_compactor(chat_history)
        return self._config.injector(
            repositories=self._repositories,
            chat_history=chat_history,
            memory_compactor=memory_compactor,
            tool_scratchpad=self._tool_scratchpad,
        )

    def _build_agent_callback_handler(self) -> Optional[BaseCallbackHandler]:
        if not self._config.agent_callback_handler:
            return None
        if issubclass(self._config.agent_callback_handler.handler_class, ConversationCallbackHandler):
            return self._config.agent_callback_handler.handler_class(conversation_id=self.conversation_id)
        return self._config.agent_callback_handler.handler_class()

    def _build_llm_callback_handlers(self) -> Optional[list[BaseCallbackHandler]]:
        if not self._config.llm.callbacks:
            return None
        handlers = []
        for config in self._config.llm.callbacks:
            if issubclass(config.handler_class, ConversationCallbackHandler):
                handler = config.handler_class(conversation_id=self.conversation_id)
            else:
                handler = config.handler_class()
            handlers.append(handler)
        return handlers

    def _build_chat_history(self) -> BaseChatMessageHistory:
        return self._config.memory.chat_history_class(self._repositories.conversation, self.conversation_id)

    def _build_memory_compactor(self, chat_history: BaseChatMessageHistory) -> Optional[BaseMemoryCompactor]:
        if not self._config.memory_compactor_enabled:
            return None
        if self._config.memory.compactor_class is None:
            raise ValueError(
                "memory_compactor_enabled is True but memory.compactor_class is not set — "
                "declare a BaseMemoryCompactor implementation in the agent config."
            )
        llm = self._build_default_llm()
        return self._config.memory.compactor_class(
            self._repositories.conversation, self.conversation_id, llm, chat_history
        )
