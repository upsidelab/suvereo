# ADR-0002: Agentic execution as a concept separate from conversations

## Status

Accepted

## Context

AI chatbot conversations are not a good fit for programmatic integration: they require human interaction, and their output is free-form text rather than a structured result a calling system can rely on.

We wanted a programmatic way of using AI agents. The AI workflow is a black box to the caller, who needs to trigger a task and retrieve its result through an API. This makes repeatable AI tasks easy to integrate into other systems.

## Decision

An agentic execution is an autonomous, API-triggered run of an agent.

- **Self-contained.** It takes only an initial, structured input. There is no user in the loop.
- **Runs to a definite outcome.** It carries the agent to the task's success or failure and produces a structured result, or a failure code with an explanation. It does not end half-finished.
- **Asynchronous.** The API triggers a run and retrieves its result. A run is tracked through `pending`, `in_progress`, and `finished` or `failed`, and executes in the background (Celery).
- **Defined separately from the agent.** An execution definition is a class of its own, bound to an agent type through `AGENT_KEY` and selected by `execution_key`. One agent plugin can offer several definitions. A definition declares its input type, its validators and the retry budget.
- **Contracts in `enthusiast-common`.** Definitions subclass `BaseAgenticExecutionDefinition` and are registered in `AVAILABLE_AGENTIC_EXECUTION_DEFINITIONS` (see [ADR-0001](0001-plugin-architecture.md)).

The server runs a definition on top of a regular `Conversation` record, so it reuses the agent-building machinery. The agent is driven by the definition rather than by a person.

## Consequences

- An agent is not automatically available for agentic execution. Each execution needs its own definition, written alongside the agent that carries it out.
- Because no one can correct the agent mid-run, a definition defines what success means. Validators check the agent's output and send feedback back to the agent, and the run is retried up to `MAX_RETRIES` times before it fails.
- Executions have their own API and status lifecycle, separate from conversations, and are authorized through the same permission mechanism as the rest of the API.
- Callers depend on the definition's input type and result structure as their contract, so changing them is a breaking change for those integrations.
