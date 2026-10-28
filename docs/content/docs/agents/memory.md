# Memory

An [agent](/docs/concepts#agent) keeps the context of a [conversation](/docs/concepts#conversation) through two mechanisms: the **persistent chat history**, which is on by default, and the **memory compactor**, which is optional.

## Context window

On every turn, the agent sends the language model these messages, in this order:

1. **The system prompt** of the agent, see [Prompts](/docs/agents/prompts). It is passed separately from the chat history.
2. (optional) **A summary of the earlier conversation**, sent as a second system message. It is included only when the [memory compactor](#memory-compactor) is enabled and has produced a summary.
3. **The most recent messages** of the chat history, trimmed to a budget of 3000 tokens.
4. **The new message** from the person.

## Chat History

`PersistentChatHistory`, a `BaseChatMessageHistory`, stores every message of the conversation in the database. It is available to agents and tools as `chat_history` on the [injector](/docs/agents/injector).

- It stores all message types: human, AI, tool calls, tool results and intermediate steps.
- It interleaves parallel tool calls with their results, so the conversation is reconstructed correctly.
- `messages_after(message_id)` returns the messages added after a given one, which the compactor uses to summarize incrementally.

## Context Window Builder

`ContextWindowBuilder` assembles the messages for each turn. It is part of the `enthusiast-agent-tool-calling` plugin, and `BaseToolCallingAgent` uses it.

- It keeps the most recent messages that fit the token budget, starting on a human message.
- It counts tokens approximately.
- When the compactor has a summary, it adds it at the start as a `SystemMessage`.

The budget is `MAX_HISTORY_TOKENS`, set to 3000 in `base_tool_calling_agent.py`.

```python
context_messages = ContextWindowBuilder(
    chat_history=self._injector.chat_history,
    memory_compactor=self._injector.memory_compactor,
).build(max_tokens=MAX_HISTORY_TOKENS)
```

## Memory Compactor

The memory compactor keeps a summary of the conversation, written by the language model and stored with the conversation. It is meant to be used together with the trimming above: the trimming keeps recent messages, and the summary carries what was said before them.

### How it works

After each turn, the agent calls `compact_if_needed()`. Once 10 human messages have been added since the last summary, the compactor asks the language model for a new one. The summary is stored on the `Conversation` record and added to the context of each following turn.

Summaries are incremental. A new one is built from the previous summary and the messages added since, so the cost of a compaction does not grow with the length of the conversation.

### Enabling the compactor

The compactor is off by default. An agent turns it on with `memory_compactor_enabled` in the configuration returned by its config provider:

```python
def get_config(self, config_type: ConfigType = ConfigType.CONVERSATION) -> AgentConfigWithDefaults:
    return AgentConfigWithDefaults(
        agent_class=ArticlesAgent,
        system_prompt=ARTICLES_SYSTEM_PROMPT,
        tools=ArticlesAgent.TOOLS,
        memory_compactor_enabled=True,
    )
```

The compactor class comes from `memory.compactor_class` in the configuration, which the default configuration (the Suvereo server's `DefaultAgentConfig`) sets to `LLMMemoryCompactor`. If `memory_compactor_enabled` is true and no compactor class is set, building the agent fails.

## Customization

### Custom memory compactor

To change how summaries are made, subclass `BaseMemoryCompactor` from `enthusiast-common`:

```python
class MyMemoryCompactor(BaseMemoryCompactor):
    def get_summary(self) -> Optional[str]:
        """Return the persisted summary, or None if there is none yet."""
        ...

    def compact_if_needed(self) -> None:
        """Generate and persist a new summary when the threshold is reached."""
        ...
```

Then point the configuration at it:

```python
AgentConfigWithDefaults(
    ...
    memory=MemoryConfig(
        chat_history_class=PersistentChatHistory,
        compactor_class=MyMemoryCompactor,
    ),
    memory_compactor_enabled=True,
)
```

Alternatively, the class can be set as the default compactor, by using it as `compactor_class` in the `memory` of the Suvereo server's `DefaultAgentConfig` (`server/agent/core/agents/default_config.py`). It is then used by every agent whose configuration leaves `memory` empty.

The builder creates the compactor as `compactor_class(conversation_repo, conversation_id, llm, chat_history)`.

### Custom injector

The injector exposes `chat_history` and `memory_compactor`. The default `Injector` already carries both, so a [vertical's](/docs/concepts#vertical) injector that extends it can pass them along, see [Injector](/docs/agents/injector).
