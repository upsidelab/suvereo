---
sidebar_position: 2
---

# Concepts

This page explains the concepts and terminology used across the AgentCore documentation and codebase.

## Data set

A data set is a workspace. It holds the [agents](#agent) and [integrations](#integration) of one company, brand or department, together with the content they work on. It also carries the settings of the language model that agents use and of the embedding model, which turns content into numbers so it can be searched by meaning.

Data sets are separate from each other: an agent only uses content that belongs to its own data set, and access can be limited to a single data set. A single data set is enough to get started. Further data sets are useful for separate brands, for separate content languages or for trying out different models.

## Agent

An agent is an AI assistant set up for a specific job. It can be defined on top of a [vertical](#vertical) or directly on top of AgentCore. Its definition specifies the [tools](#tool) it can call and the settings it accepts. Each agent has a name, a description and values for those settings, and belongs to one [data set](#data-set).

An agent does its job by calling tools. People talk to agents in [conversations](#conversation), and other systems start them in [agentic executions](#agentic-execution).

## Tool

A tool is a capability an agent can call while it works: searching content, reading a file, calling an external service or handing a task to another agent. Tools can come with the agent definition, from [integrations](#integration) such as MCP servers, and from the [vertical](#vertical) the agent is built on.

## Conversation

A conversation is an interactive exchange between a person and an agent in the web UI. Answers are streamed as the agent writes them, and the history is saved. People can attach files for the agent to work with.

## Agentic execution

An agentic execution is an autonomous run of an agent, started through the API with structured input and returning a structured result. No one takes part in the run. It happens in the background and moves through the statuses `pending`, `in_progress` and then `finished` or `failed`.

An agent definition can offer several kinds of execution, and the caller picks one with an `execution_key`. Executions suit work that arrives in batches or from other systems, such as processing a stream of documents.

## Integration

An integration is a configured connection to an external system on a data set.
Integrations serve two purposes:

- **Bringing content in.** A source integration syncs content from an external system. The content is stored as [entities](#entity) and indexed for search.
- **Letting agents act.** An integration can give agents tools for working in the external system.

AgentCore includes a ready-made integration for MCP servers. An MCP server is an external server that exposes tools through the Model Context Protocol. Once it is connected to a data set by signing in with OAuth, its tools are available to the data set's agents.

## Entity

An entity is a kind of record in a domain, such as an article or a support ticket. AgentCore defines no entities of its own: they come from a [vertical](#vertical). AgentCore stores the entities, lists them in the UI and indexes their content, so agents can retrieve what is relevant to a question.

## Vertical

A vertical adds a domain to AgentCore. It can define the domain's entities, its integrations with external systems, and how both are handed to agents as tools. Everything else, including conversations, agentic executions, permissions, models and the UI, comes from AgentCore.

A vertical is enabled in the instance settings, and agents are then built on top of it. AgentCore also runs without a vertical, with agents that use the basic tools it provides and the tools of any connected MCP server.

[Enthusiast](/tools/enthusiast) is the vertical for e-commerce. It defines products and documents.

## Plugin

A plugin is a standalone package that extends AgentCore without changing it. Plugins can supply language and embedding model providers, integrations, agent definitions and verticals. All of them are built against shared contracts, which is how AgentCore loads them and how they stay independent of each other.
