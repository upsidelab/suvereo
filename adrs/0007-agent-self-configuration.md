# ADR-0007: Agents declare their own configuration

## Status

Accepted

## Context

The agent configuration mechanism was previously over-complicated.

Registering an agent took a config provider class next to the agent, found by the registry through module-path convention, plus an optional builder and a prompt formatted by hooks on the agent. The agent, provider and builder referenced each other, and `AgentConfig` named the agent class that produced it. This raised the bar for writing a new agent.

## Decision

- **The agent is the unit of configuration.** `BaseAgent` declares `SYSTEM_PROMPT`, `TOOLS`, `BUILDER_CLASS`, `CONVERSATION_HISTORY_TOKEN_LIMIT` and `MEMORY_COMPACTOR_ENABLED` as class variables. The framework's `BaseAgent.get_config()` turns them into an `AgentConfig`. An agent whose configuration the variables cannot express overrides `get_config()`. There is no config provider class.
- **The execution definition owns execution-mode settings.** `BaseAgenticExecutionDefinition` declares an optional `SYSTEM_PROMPT` and `TOOLS` (see [ADR-0008](0008-tool-configuration-keyed-by-tool-name.md)), applied on top of the agent's configuration through `AgentConfigOverrides` (see [ADR-0002](0002-agentic-execution.md)). Each execution of an agent can differ, and the agent has a single configuration.
- **`agent_class` is not part of `AgentConfig`.** The builder receives it as a separate constructor argument, so a config cannot name another class than the one it was built for.

## Consequences

- An agent is one class: its configuration is readable in the class body, and registering it takes one entry in `AVAILABLE_AGENTS`.
- A setting that varies between a conversation and an execution belongs on the execution definition; logic beyond the class variables goes in an overridden `get_config()`.
- An execution definition that sets no `SYSTEM_PROMPT` runs with the agent's conversation prompt.
- `BaseAgentConfigProvider` and `ConfigType` are removed, and the builder constructor changed: agent plugins outside this repository must migrate.
