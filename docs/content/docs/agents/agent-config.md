# Agent Configuration

`AgentConfig` describes how an [agent](/docs/concepts#agent) is assembled: which class runs it, which prompt and tools it uses, and which classes provide its injector, repositories, registries and memory. The [builder](/docs/agents/builder) reads it when it creates the agent.

An agent implementation does not need to fill in the whole configuration. It can return an `AgentConfigWithDefaults` with only the fields that are specific to the agent, and the framework fills in the rest from its defaults.

## AgentConfig

`AgentConfig` is a Pydantic model.

```python
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
    conversation_history_token_limit: int = Field(gt=0)
    memory_compactor_enabled: bool = False
    similarity_searcher: Optional[Type[BaseSimilaritySearcher]] = None
    integration_plugin_resolver: Optional[Type[BaseIntegrationPluginResolver]] = None
```

| Field | Description |
|---|---|
| `agent_class` | The agent class to instantiate, for example a subclass of `BaseToolCallingAgent`. |
| `llm` | `LLMConfig`: the language model class and optional callback handlers. |
| `repositories` | `RepositoriesConfig`: the repository class for each entity the agent can read: `user`, `message`, `conversation`, `data_set` and `agent`. |
| `injector` | The injector class, see [Injector](/docs/agents/injector). |
| `registry` | `RegistryConfig`: the registries for language models, embedding providers and database models. |
| `system_prompt` | The system prompt. It can contain `{variable}` placeholders, see [Prompts](/docs/agents/prompts). |
| `memory` | `MemoryConfig`: the chat history class and, optionally, the memory compactor class. |
| `tools` | The tools of the agent, as `FunctionToolConfig`, `LLMToolConfig`, `AgentToolConfig` or `FileToolConfig`. See [Tools](/docs/agents/tools). |
| `agent_callback_handler` | Receives agent events. By default, it streams them to the conversation. |
| `conversation_history_token_limit` | The number of tokens of recent chat history sent to the language model on each turn, see [Memory](/docs/agents/memory#context-window-builder). Must be greater than 0. |
| `memory_compactor_enabled` | Turns on the memory compactor for this agent. Off by default, see [Memory](/docs/agents/memory). |
| `similarity_searcher` | The class that runs similarity search for retrievers. |
| `integration_plugin_resolver` | The class that finds the [integrations](/docs/concepts#integration) connected to a data set, used to attach their tools to the agent. |

## Defaults

`AgentConfigWithDefaults` keeps `agent_class` and `system_prompt` required: they have no default, so every agent supplies its own. It makes `repositories`, `injector`, `registry`, `llm`, `memory` and `conversation_history_token_limit` optional, and the framework replaces every field left empty with the value from its default configuration, defined in `server/agent/core/agents/default_config.py`:

| Field | Default |
|---|---|
| `repositories` | Django repositories for users, messages, conversations, data sets and agents |
| `injector` | `Injector` |
| `registry` | `LanguageModelRegistry`, `EmbeddingProviderRegistry` and `BaseDjangoSettingsDBModelRegistry` |
| `llm` | `BaseLLM` |
| `memory` | `PersistentChatHistory` and `LLMMemoryCompactor` |
| `conversation_history_token_limit` | The `DEFAULT_CONVERSATION_HISTORY_TOKEN_LIMIT` instance setting, 10,000 tokens unless changed |
| `agent_callback_handler` | `ConversationWebSocketCallbackHandler` |
| `similarity_searcher` | `EmbeddingSimilaritySearcher` |
| `integration_plugin_resolver` | `IntegrationPluginResolver` |

An agent built on a [vertical](/docs/concepts#vertical) usually sets none of these except the agent class, prompt and tools. The vertical's builder, declared in the config provider, can take care of its own injector.

## Configuration Provider

An agent implementation provides its configuration through a subclass of `BaseAgentConfigProvider` from `enthusiast_common.agents`.

- It implements `get_config(config_type) -> AgentConfigWithDefaults`.
- It can set `BUILDER_CLASS` to a builder class. Without it, the default `AgentBuilder` is used.
- It must be importable from the same module as the agent class registered in `AVAILABLE_AGENTS`.

The registry derives the module from `AVAILABLE_AGENTS`: it strips the class name from each path and scans the module for a `BaseAgentConfigProvider` subclass. With `AVAILABLE_AGENTS = ["articles_agent.ArticlesAgent"]`, it looks in `articles_agent`. File names and directory layout are not restricted, as long as the provider can be imported from that module, for example through `__init__.py`.

```python
# config.py
class ArticlesConfigProvider(BaseAgentConfigProvider):
    BUILDER_CLASS = ArticlesAgentBuilder

    def get_config(self, config_type: ConfigType = ConfigType.CONVERSATION) -> AgentConfigWithDefaults:
        return AgentConfigWithDefaults(
            agent_class=ArticlesAgent,
            system_prompt=ARTICLES_SYSTEM_PROMPT,
            tools=ArticlesAgent.TOOLS,
        )
```

```python
# __init__.py
from .agent import ArticlesAgent
from .config import ArticlesConfigProvider

__all__ = ["ArticlesAgent", "ArticlesConfigProvider"]
```

### Configuration per context

`get_config` receives a `config_type` that tells which kind of run needs the agent:

- `ConfigType.CONVERSATION`: an interactive [conversation](/docs/concepts#conversation), the default
- `ConfigType.AGENTIC_EXECUTION_DEFINITION`: an autonomous [agentic execution](/docs/concepts#agentic-execution)

An agent that behaves differently in the two contexts returns a different configuration for each:

```python
def get_config(self, config_type: ConfigType = ConfigType.CONVERSATION) -> AgentConfigWithDefaults:
    if config_type == ConfigType.AGENTIC_EXECUTION_DEFINITION:
        return AgentConfigWithDefaults(
            agent_class=ArticlesAgent,
            system_prompt=ARTICLES_EXECUTION_PROMPT,
            tools=ArticlesAgent.TOOLS + [LLMToolConfig(tool_class=StopExecutionTool)],
        )
    return AgentConfigWithDefaults(
        agent_class=ArticlesAgent,
        system_prompt=ARTICLES_SYSTEM_PROMPT,
        tools=ArticlesAgent.TOOLS,
    )
```
