# Builder

The builder creates a ready [agent](/docs/concepts#agent) from its [configuration](/docs/agents/agent-config): the repositories, registries, language models, injector, tools and callback handlers. It is created for a conversation, so it can read the conversation's data set and the agent's stored settings.

## Base Agent Builder

`BaseAgentBuilder` is the contract every builder satisfies. It fixes the constructor and a `build()` method, and nothing else:

```python
class BaseAgentBuilder(ABC, Generic[ConfigT]):
    def __init__(
        self,
        config: ConfigT,
        conversation_id: Any,
        streaming: bool = False,
        tool_scratchpad: Optional[ToolScratchpad] = None,
    ): ...

    @abstractmethod
    def build(self) -> BaseAgent:
        """Build and return a fully wired agent for the conversation."""
```

An agent can point its `BUILDER_CLASS` at any class that satisfies this contract.

## Default Agent Builder

`AgentBuilder` is the default implementation. Every host-specific piece reaches it through the configuration, so it depends only on contracts from `suvereo-common`. Agents that declare no `BUILDER_CLASS` use it.

`build()` runs these steps:

```python
def build(self) -> BaseAgent:
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
```

- **Repositories** are created from the classes in the configuration, each bound to its database model.
- **The agent's language model** streams its answer when `streaming` is true. **The default language model** is the one tools use unless a tool's config sets its own `llm`.
- **Tools** are created according to the type of their config: `FunctionToolConfig`, `LLMToolConfig`, `FileToolConfig` or `AgentToolConfig`. A sub-agent of an `AgentToolConfig` is built with the same builder class as its parent.
- **Stored settings** entered in the UI are applied to the agent and its tools as the last step.

`abuild()` is the async twin. It runs `build()` in a worker thread and then attaches the tools of the [integrations](/docs/concepts#integration) connected to the data set, such as MCP servers. Each integration has ten seconds to answer. One that fails or times out contributes no tools for that turn, and the others are not affected.

## Extending the builder

A [vertical](/docs/concepts#vertical) can subclass `AgentBuilder` to create the extra resources of its [domain](/docs/concepts#domain). Most of the time only `_build_injector()` is overridden:

```python
class ArticlesAgentBuilder(AgentBuilder[AgentConfig]):
    def _build_injector(self) -> ArticlesInjector:
        chat_history = self._build_chat_history()
        return ArticlesInjector(
            article_retriever=ArticleRetriever(
                data_set_id=self._data_set_id,
                embeddings_registry=self._embeddings_registry,
                searcher=self._config.similarity_searcher(),
            ),
            repositories=self._repositories,
            chat_history=chat_history,
            memory_compactor=self._build_memory_compactor(chat_history),
            tool_scratchpad=self._tool_scratchpad,
        )
```

The builder is attached to an agent through its `BUILDER_CLASS` class variable:

```python
class ArticlesAgent(BaseToolCallingAgent):
    BUILDER_CLASS = ArticlesAgentBuilder
```

See [Injector](/docs/agents/injector) for the injector this builder creates.
