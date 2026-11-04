# Agent Architecture

This page describes the parts an [agent](/docs/concepts#agent) is made of and how they fit together. Each part has its own page.

## Overview

When a [conversation](/docs/concepts#conversation) or an [agentic execution](/docs/concepts#agentic-execution) needs an agent, a builder assembles it from the agent's configuration. The agent class declares its own settings, such as its system prompt and [tools](/docs/concepts#tool), and the framework adds defaults for the rest: the classes used for the injector, repositories, registries and memory. The default builder creates all of these parts and hands them to the agent.

| Part | What it is | Page |
|---|---|---|
| Agent | The class that receives a message, calls tools and produces the answer. | [Agent Classes](/docs/agents/agent-classes) |
| Configuration | `AgentConfig`: everything the builder needs to assemble the agent. | [Agent Configuration](/docs/agents/agent-config) |
| System prompt | A string that sets the agent's role and behavior. | [Prompts](/docs/agents/prompts) |
| Tools | The capabilities the agent can call. | [Tools](/docs/agents/tools) |
| Injector | The container that gives the agent and its tools access to repositories, chat history and memory. | [Injector](/docs/agents/injector) |
| Memory | Persistent chat history and the optional memory compactor. | [Memory](/docs/agents/memory) |
| Builder | Creates every part above and returns a ready agent. | [Builder](/docs/agents/builder) |

## How an agent is built

`AgentBuilder.build()` performs these steps:

1. Create the database models registry and the repositories, and resolve the [data set](/docs/concepts#data-set) of the conversation.
2. Create the language model and embeddings registries.
3. Create the language model for the agent, and a default language model for tools.
4. Create the injector.
5. Create the tools listed in the configuration.
6. Create the callback handler and the agent instance.
7. Apply the agent's stored settings, which are entered in the UI, to the agent and its tools.

When an agent has [integrations](/docs/concepts#integration) that provide tools, such as MCP servers, selected under **Tool sources** in its settings, it is built with `abuild()`, which also attaches the tools of those integrations.

## Where a vertical fits

The core injector carries repositories, chat history, the memory compactor and the tool scratchpad. It holds no [domain](/docs/concepts#domain) data. A [vertical](/docs/concepts#vertical) can extend the injector with its own retrievers and connectors, and supply a builder that creates them. Agents built on the vertical can then reach the domain's data through the injector. See [Injector](/docs/agents/injector) and [Builder](/docs/agents/builder).
