from typing import Optional

from enthusiast_common.agents import BaseAgent
from enthusiast_common.builder import BaseAgentBuilder, RepositoriesInstances
from enthusiast_common.callbacks import ConversationCallbackHandler
from enthusiast_common.config import (
    AgentConfig,
    AgentToolConfig,
    FileToolConfig,
    FunctionToolConfig,
    LLMConfig,
    LLMToolConfig,
)
from enthusiast_common.injectors import BaseInjector
from enthusiast_common.registry import BaseDBModelsRegistry, BaseEmbeddingProviderRegistry, BaseLanguageModelRegistry
from enthusiast_common.tools import BaseAgentTool, BaseFileTool, BaseFunctionTool, BaseLLMTool
from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.language_models import BaseLanguageModel
from langchain_core.tools import BaseTool

from agent.core.memory import LLMMemoryCompactor, PersistentChatHistory


class AgentBuilder(BaseAgentBuilder[AgentConfig]):
    def _build_agent(
        self,
        tools: list[BaseTool],
        llm: BaseLanguageModel,
        callback_handler: BaseCallbackHandler,
    ) -> BaseAgent:
        return self._config.agent_class(
            tools=tools,
            llm=llm,
            system_prompt=self._config.system_prompt,
            conversation_id=self.conversation_id,
            callback_handler=callback_handler,
            injector=self._injector,
        )

    def _build_llm_registry(self) -> BaseLanguageModelRegistry:
        llm_registry_class = self._config.registry.llm.registry_class
        data_set_repo = self._repositories.data_set
        if providers := self._config.registry.llm.providers:
            llm_registry = llm_registry_class(providers=providers)
        else:
            llm_registry = llm_registry_class(data_set_repo=data_set_repo)
        return llm_registry

    def _build_db_models_registry(self) -> BaseDBModelsRegistry:
        db_models_registry_class = self._config.registry.model.registry_class
        if models_config := self._config.registry.model.models_config:
            db_model_registry = db_models_registry_class(models_config=models_config)
        else:
            db_model_registry = db_models_registry_class()
        return db_model_registry

    def _build_and_set_repositories(self, models_registry: BaseDBModelsRegistry) -> None:
        repositories = {}
        for name in self._config.repositories.__class__.model_fields.keys():
            repo_class = getattr(self._config.repositories, name)
            model_class = models_registry.get_model_class_by_name(name)
            repositories[name] = repo_class(model_class)
        self._repositories = RepositoriesInstances(**repositories)

    def _build_embeddings_registry(self) -> BaseEmbeddingProviderRegistry:
        embeddings_registry_class = self._config.registry.embeddings.registry_class
        data_set_repo = self._repositories.data_set
        if providers := self._config.registry.llm.providers:
            embeddings_registry = embeddings_registry_class(providers=providers)
        else:
            embeddings_registry = embeddings_registry_class(data_set_repo=data_set_repo)
        return embeddings_registry

    def _build_llm(self, llm_config: LLMConfig) -> BaseLanguageModel:
        data_set_repo = self._repositories.data_set
        callbacks = self._build_llm_callback_handlers()
        llm = llm_config.llm_class(
            llm_registry=self._llm_registry,
            callbacks=callbacks,
            streaming=self.streaming,
            data_set_repo=data_set_repo,
        )
        return llm.create(self._data_set_id)

    def _build_default_llm(self) -> BaseLanguageModel:
        llm_registry_class = self._config.registry.llm.registry_class
        data_set_repo = self._repositories.data_set
        if providers := self._config.registry.llm.providers:
            llm_registry = llm_registry_class(providers=providers)
        else:
            llm_registry = llm_registry_class(data_set_repo=data_set_repo)

        llm = self._config.llm.llm_class(
            llm_registry=llm_registry,
            data_set_repo=data_set_repo,
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
        agent = AgentBuilder(config.agent, self.conversation_id, self.streaming).build()
        return config.tool_class(agent=agent)

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
        else:
            return self._config.agent_callback_handler.handler_class()

    def _build_llm_callback_handlers(self) -> Optional[list[BaseCallbackHandler]]:
        if not self._config.llm.callbacks:
            return None
        callbacks_config = self._config.llm.callbacks
        handlers = []
        for config in callbacks_config:
            if issubclass(config.handler_class, ConversationCallbackHandler):
                handler = config.handler_class(conversation_id=self.conversation_id)
            else:
                handler = config.handler_class()
            handlers.append(handler)
        return handlers

    def _build_chat_history(self) -> PersistentChatHistory:
        return PersistentChatHistory(self._repositories.conversation, self.conversation_id)

    def _build_memory_compactor(self, chat_history: PersistentChatHistory) -> Optional[LLMMemoryCompactor]:
        if not self._config.memory_compactor_enabled:
            return None
        llm = self._build_default_llm()
        return LLMMemoryCompactor(self._repositories.conversation, self.conversation_id, llm, chat_history)

