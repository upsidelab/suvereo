# Agent Configuration

`AgentConfig` describes how an [agent](/docs/concepts#agent) is assembled: which prompt and tools it uses, and which classes provide its injector, repositories, registries and memory. The [builder](/docs/agents/builder) reads it when it creates the agent.

The agent class is the unit of configuration. It declares the settings that are specific to it as class variables, and the framework turns them into an `AgentConfig` and fills in the rest from its defaults.

## AgentConfig

`AgentConfig` is a Pydantic model.

```python
class AgentConfig(ArbitraryTypeBaseModel, Generic[InjectorT]):
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

`AgentConfigWithDefaults` keeps `system_prompt` required: it has no default, so every agent supplies its own. It makes `repositories`, `injector`, `registry`, `llm`, `memory` and `conversation_history_token_limit` optional, and the framework replaces every field left empty with the value from its default configuration, defined in `server/agent/core/agents/default_config.py`:

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

An agent built on a [vertical](/docs/concepts#vertical) usually sets none of these except the prompt and tools. The vertical's builder, declared as `BUILDER_CLASS` on the agent, can take care of its own injector.

## Declaring the configuration on the agent

An agent class declares its configuration as class variables:

| Variable | Required | Becomes |
|---|---|---|
| `SYSTEM_PROMPT` | Yes | `system_prompt`, see [Prompts](/docs/agents/prompts) |
| `TOOLS` | No | `tools`, see [Tools](/docs/agents/tools) |
| `CONVERSATION_HISTORY_TOKEN_LIMIT` | No | `conversation_history_token_limit`. `None` keeps the default above |
| `MEMORY_COMPACTOR_ENABLED` | No | `memory_compactor_enabled`, `False` by default |
| `BUILDER_CLASS` | No | Not part of `AgentConfig`: the builder that assembles the agent. Without it, the default `AgentBuilder` is used |

`NAME` and `AGENT_KEY` are required as well, see [Agent Classes](/docs/agents/agent-classes#class-variables). A concrete agent class that leaves a required variable undefined or empty fails when it is imported.

```python
class ArticlesAgent(BaseToolCallingAgent):
    NAME = "Articles"
    AGENT_KEY = "articles-agent"
    SYSTEM_PROMPT = ARTICLES_SYSTEM_PROMPT
    TOOLS = [LLMToolConfig(tool_class=SearchArticlesTool)]
    BUILDER_CLASS = ArticlesAgentBuilder
    MEMORY_COMPACTOR_ENABLED = True
```

`BaseAgent.get_config()` reads these variables and returns an `AgentConfigWithDefaults`. An agent whose configuration the variables cannot express can override it:

```python
class ArticlesAgent(BaseToolCallingAgent):
    @classmethod
    def get_config(cls) -> AgentConfig:
        config = super().get_config()
        config.tools = [*cls.TOOLS, *tools_for_current_deployment()]
        return config
```

## Registering the agent

An agent is registered by adding its dotted path to `AVAILABLE_AGENTS`; nothing else needs to be exported next to it:

```python
AVAILABLE_AGENTS = ["articles_agent.ArticlesAgent"]
```
