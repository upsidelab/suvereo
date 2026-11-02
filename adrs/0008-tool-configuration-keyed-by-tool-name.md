# ADR-0008: Tool configuration keyed by tool name

## Status

Accepted

## Context

An agent stored its tools' settings as a list, `config.tools`, applied to its built tools by position. Reordering `TOOLS`, inserting a tool, or an execution adding tools shifted stored settings onto another tool. Executions could only append tools to the agent's (`EXTRA_TOOLS`), and a tool they added had nowhere to store settings.

## Decision

- **Tool settings are a map keyed by tool `NAME`.** `config.tools` is `{NAME: {field: value}}`, with one entry per configurable tool (a tool whose `CONFIGURATION_ARGS` is set). `BaseAgent.set_runtime_arguments` gives each built tool its entry by `NAME`.
- **The tool declares its settings, the agent holds the values.** `CONFIGURATION_ARGS` stays on the tool; the agent's stored config, form and validation hold every value its tools use.
- **An execution declares its own tool list.** `BaseAgenticExecutionDefinition.TOOLS` replaces `EXTRA_TOOLS`: `None` runs the agent's tools, a list replaces them.
- **The agent configures the tools of its executions.** An agent's configurable tools are its `TOOLS` plus the `TOOLS` of every installed execution with its `AGENT_KEY`. A shared tool uses the agent's values.

## Consequences

- Tool order in `TOOLS` carries no meaning for stored data.
- Renaming a tool's `NAME` needs a data migration of its stored settings.
- An agent and its executions use one `NAME` for one tool settings schema; a startup check reports a conflict.
- Installing an execution that adds a configurable tool leaves saved agents without its settings; the agent list marks them corrupted until their form is saved.
- Agent plugins outside this repository that set `EXTRA_TOOLS` must move to `TOOLS`; `BaseAgenticExecutionDefinition` raises `TypeError` at import for a definition that still sets it.
