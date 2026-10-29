# Injector

The injector is the container that gives an [agent](/docs/concepts#agent) and its [tools](/docs/concepts#tool) access to the resources they work with. The agent receives it when it is built, and tools receive it through their constructor.

Suvereo defines no [domain](/docs/concepts#domain) data, so the injector it provides carries only the resources every agent needs. A [vertical](/docs/concepts#vertical) can extend it with the resources of its domain, such as retrievers that search the vertical's [entities](/docs/concepts#entity).

## Base Injector

`BaseInjector` is the contract every injector satisfies:

```python
class BaseInjector(ABC):
    def __init__(self, repositories: RepositoriesInstances):
        self.repositories = repositories

    @property
    @abstractmethod
    def chat_history(self) -> BaseChatMessageHistory: ...

    @property
    @abstractmethod
    def memory_compactor(self) -> Optional[BaseMemoryCompactor]: ...

    @property
    @abstractmethod
    def tool_scratchpad(self) -> ToolScratchpad: ...
```

| Resource | Description |
|---|---|
| `repositories` | Data access for users, messages, conversations, data sets and agents. |
| `chat_history` | The persistent history of the [conversation](/docs/concepts#conversation). See [Memory](/docs/agents/memory). |
| `memory_compactor` | The summary of earlier messages. `None` unless the agent enables it. See [Memory](/docs/agents/memory). |
| `tool_scratchpad` | A store that tools write to and validators read from during an [agentic execution](/docs/concepts#agentic-execution). |

## Default Injector

`Injector` is the default implementation. The default configuration uses it for every agent that does not set its own. It takes the repositories, the chat history and, optionally, the tool scratchpad and the memory compactor.

```python
class Injector(BaseInjector):
    def __init__(
        self,
        repositories: RepositoriesInstances,
        chat_history: BaseChatMessageHistory,
        tool_scratchpad: Optional[ToolScratchpad] = None,
        memory_compactor: Optional[BaseMemoryCompactor] = None,
    ): ...
```

## Using the injector

Tools receive the injector through their constructor. A tool reads what it needs from it:

```python
class EmptyInput(BaseModel):
    pass


class MessageCountTool(BaseLLMTool):
    NAME = "count_messages"
    DESCRIPTION = "Return the number of messages exchanged so far in the conversation."
    ARGS_SCHEMA = EmptyInput
    RETURN_DIRECT = False

    def run(self) -> str:
        return str(len(self._injector.chat_history.messages))
```

An agent reaches the same resources through `self._injector`. `BaseToolCallingAgent`, for example, reads `chat_history` and `memory_compactor` to build the context of each turn.

## Extending the injector

A vertical can subclass `Injector` to add the resources of its domain. This example adds a retriever that searches articles:

```python
class ArticlesInjector(Injector):
    def __init__(self, *args, article_retriever: ArticleRetriever, **kwargs):
        super().__init__(*args, **kwargs)
        self._article_retriever = article_retriever

    @property
    def article_retriever(self) -> ArticleRetriever:
        return self._article_retriever
```

Tools of agents built on this vertical can then use the retriever:

```python
class SearchArticlesInput(BaseModel):
    query: str = Field(description="What to look for in the articles")


class SearchArticlesTool(BaseLLMTool):
    NAME = "search_articles"
    DESCRIPTION = "Find articles relevant to a question."
    ARGS_SCHEMA = SearchArticlesInput
    RETURN_DIRECT = False

    def run(self, query: str) -> str:
        chunks = self._injector.article_retriever.find_content_matching_query(query)
        return "\n\n".join(f"{c.article.title}\n{c.content}" for c in chunks) or "No matching articles."
```

The injector is created by the builder. A vertical can override the builder's `_build_injector()` to pass its extra resources, see [Builder](/docs/agents/builder).
