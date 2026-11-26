# Memory

An [agent](/docs/concepts#agent) keeps the context of a [conversation](/docs/concepts#conversation) through two mechanisms: the **persistent chat history**, which is on by default, and the **memory compactor**, which is optional.

## Context window

On every turn, the agent sends the language model these messages, in this order:

1. **The system prompt** of the agent, see [Prompts](/docs/agents/prompts). It is passed separately from the chat history.
2. (optional) **A summary of the earlier conversation**, sent as a second system message. It is included only when the [memory compactor](#memory-compactor) is enabled and has produced a summary.
3. **The most recent messages** of the chat history, trimmed to the conversation history token limit, see [Context Window Builder](#context-window-builder). If the memory compactor is enabled for the agent, the messages that are already summarized are by default not included, to prevent the summary and the history from overlapping.
4. **The new message** from the person.

## Chat History

`PersistentChatHistory`, a `BaseChatMessageHistory`, stores every message of the conversation in the database. It is available to agents and tools as `chat_history` on the [injector](/docs/agents/injector).

- It stores all message types: human, AI, tool calls, tool results and intermediate steps.
- It interleaves parallel tool calls with their results, so the conversation is reconstructed correctly.
- `messages` returns only the messages the conversation summary does not cover yet. Without a summary, which is always the case when the compactor is off, it returns the whole conversation.
- `messages_after(message_id)` returns the messages added after a given one, and `messages_after(None)` the whole conversation.

## Context Window Builder

`ContextWindowBuilder` assembles the messages for each turn. It is part of the `suvereo-agent-tool-calling` plugin, and `BaseToolCallingAgent` uses it.

- It keeps the most recent messages that fit the token limit, starting on a human message.
- It counts tokens approximately.
- It reads `chat_history.messages`, which leaves out the messages the summary covers, so the summary and the messages never overlap.
- When the compactor has a summary, it adds it at the start as a `SystemMessage`.

The limit is the agent's `conversation_history_token_limit`. By default it is 10,000 tokens, the value of the `DEFAULT_CONVERSATION_HISTORY_TOKEN_LIMIT` instance setting, which can be set through an environment variable of the same name. An agent can use a different limit by setting the `CONVERSATION_HISTORY_TOKEN_LIMIT` class variable, see [Agent Configuration](/docs/agents/agent-config).

```python
context_messages = ContextWindowBuilder(
    chat_history=self._injector.chat_history,
    memory_compactor=self._injector.memory_compactor,
).build(max_tokens=self._conversation_history_token_limit)
```

## Memory Compactor

The memory compactor keeps a summary of the older part of the conversation, written by the language model and stored with the conversation. The default implementation is `LLMMemoryCompactor`, which every agent that enables the compactor uses unless it sets its own, see [Enabling the compactor](#enabling-the-compactor).

### How it works

The compaction mechanism is coupled with the agent's `CONVERSATION_HISTORY_TOKEN_LIMIT`. Once the limit is exceeded, the compactor summarizes the oldest messages with the language model. By default, the compactor leaves out around 30% (token-wise) of the newest messages: they are neither included in the summary nor cut off from the message history. The purpose of that is to keep the most recent history fresh in the model's memory. The most recent turn is always left as it is.

Additionally, the summary is bound to take up at most 10% (by default) of the history token limit, to prevent it from growing uncontrollably. If the summary does not meet the length requirement, the language model is invoked again with a request to shorten it, up to 3 times. A summary that is still too long, empty or cut off is not saved, and the compaction is retried later.

The token count is approximate (about 4 characters per token). The limits mentioned above (30% and 10%) are constants of `LLMMemoryCompactor` (`RECENT_TAIL_FRACTION` and `SUMMARY_TOKEN_FRACTION`), and a custom compactor can define its own.

### When it runs

When the compactor is enabled, the agent calls `compact_if_needed()` after every turn, once the answer is stored. It checks whether the token limit is exceeded and, if so, compacts. The call runs as part of the turn, so a turn that compacts takes longer, and the conversation accepts no new message until it finishes.

A failing compaction never fails the turn: the error is logged and the turn still returns its answer. The next turn checks again.

### Enabling the compactor

The compactor is off by default. An agent turns it on with the `MEMORY_COMPACTOR_ENABLED` class variable:

```python
class ArticlesAgent(BaseToolCallingAgent):
    NAME = "Articles"
    AGENT_KEY = "articles-agent"
    SYSTEM_PROMPT = ARTICLES_SYSTEM_PROMPT
    MEMORY_COMPACTOR_ENABLED = True
```

The compactor class comes from `memory.compactor_class` in the configuration, which the default configuration (the Suvereo server's `DefaultAgentConfig`) sets to `LLMMemoryCompactor`. If the compactor is enabled and no compactor class is set, building the agent fails.

## Customization

### Custom memory compactor

To change how summaries are made, subclass `BaseMemoryCompactor` from `suvereo-common`:

```python
class MyMemoryCompactor(BaseMemoryCompactor):
    def get_summary(self) -> Optional[str]:
        """Return the persisted summary, or None if there is none yet."""
        ...

    def compact_if_needed(self) -> None:
        """Summarize the older part of the window when it has outgrown the token limit."""
        ...
```

Then point the agent's configuration at it by overriding `get_config()`:

```python
class ArticlesAgent(BaseToolCallingAgent):
    NAME = "Articles"
    AGENT_KEY = "articles-agent"
    SYSTEM_PROMPT = ARTICLES_SYSTEM_PROMPT
    MEMORY_COMPACTOR_ENABLED = True

    @classmethod
    def get_config(cls) -> AgentConfig:
        config = super().get_config()
        config.memory = MemoryConfig(
            chat_history_class=PersistentChatHistory,
            compactor_class=MyMemoryCompactor,
        )
        return config
```

Alternatively, the class can be set as the default compactor, by using it as `compactor_class` in the `memory` of the Suvereo server's `DefaultAgentConfig` (`server/agent/core/agents/default_config.py`). It is then used by every agent whose configuration leaves `memory` empty.

### Custom injector

The injector exposes `chat_history` and `memory_compactor`. The default `Injector` already carries both, so a [domain definition's](/docs/concepts#domain-definition) injector that extends it can pass them along, see [Injector](/docs/agents/injector).
