<h1 align="center">
  <a href="https://upsidelab.io/suvereo">
    <picture>
      <source media="(prefers-color-scheme: dark)" srcset=".github/assets/suvereo-logo-color-on-dark.svg">
      <img src=".github/assets/suvereo-logo-color.svg" height="60" alt="Suvereo">
    </picture>
  </a>
</h1>

<p align="center">Production Ready Agentic AI Framework.</p>
<div align="center">
  <strong>
    <a href="https://upsidelab.io/suvereo">Website</a> |
    <a href="https://upsidelab.io/suvereo/docs/getting-started/installation">Installation Guide</a> |
    <a href="https://upsidelab.io/suvereo/docs">View Docs</a>
  </strong>
</div>


## Introduction

Suvereo is an open-source framework for putting AI agents to work on your own systems. It gives agents access to your data, lets them act in your connected services, and gives your team a place to manage them, without building that infrastructure from scratch.

The core is domain-agnostic: it works for any field, from e-commerce to healthcare. You describe your domain in a **domain definition**, a package that adds its entities, its integration types and the way agents reach them. Suvereo provides everything else. You can also start without one and give agents the tools of any MCP server.

## Features

- **Conversations** - chat with an agent in the web UI, with streamed answers and saved history.
- **Agentic executions** - autonomous, API-triggered agent runs with structured input and result, checked by validators that send the agent back to correct its answer.
- **Search across your content** - content is split, embedded and searched by meaning, so agents answer from your data (RAG).
- **Integrations** - connect external systems to pull data in or to let agents act there through tools, MCP servers included.
- **Evaluation** - run an agent on a suite of cases, compare models and prompts, and catch regressions in CI.
- **Access control** - roles, groups and service accounts, scoped globally or to a data set.
- **Choice of AI models** - OpenAI, Azure OpenAI, Anthropic, Google Gemini, Mistral and self-hosted models through Ollama.
- **Plugins** - models, integrations, agents and domain definitions are installable packages built on shared contracts.
- **A standard stack** - Python, Django, PostgreSQL with pgvector, and React, with Docker Compose for development and production.

## Quick Start

The [Suvereo starter](https://upsidelab.io/suvereo/docs/customization/using-the-suvereo-starter) runs the server and the management panel with Docker Compose, and gives you a place for your own code:

```shell
git clone https://github.com/upsidelab/suvereo-starter
cd suvereo-starter
cp server/config/sample.env server/config/.env
cp frontend/config/sample.env frontend/config/.env
# set OPENAI_API_KEY in server/config/.env
docker compose build && docker compose up
```

Open the management panel at [http://localhost:10001](http://localhost:10001) and sign in as `admin@example.com` with the password `changeme`. The [installation guide](https://upsidelab.io/suvereo/docs/getting-started/installation) covers the details, and you can also book a [live demo](https://calendar.google.com/calendar/u/0/appointments/schedules/AcZssZ3NyFdPn_jqYqD24asveLkfrB1NTal0PWkLNHFTT4Fmp6sNW50-0or8WyIzBriF8IFdP1jXSPjQ) to see it in action.

## How It Works

- A **data set** scopes everything: its agents, its integrations, its content, and the model and embedding settings used for it.
- An **agent** is a configured instance of an agent type, with its prompt and tools. Users talk to it in **conversations**, and the API starts it in **agentic executions**.
- An **integration** connects a data set to an external system: it syncs content in, or gives agents tools to act there.
- A **domain definition** adds the entities of a domain, such as recipes or products, and the retrievers and integration types agents use to reach them.

Everything you add, from a model provider to a domain definition, is a plugin registered in the instance settings. See [Concepts](https://upsidelab.io/suvereo/docs/concepts) for the full picture.

## Example Domains

- **Diet advice** - recipes and user profiles, a nutrition assistant that suggests meals within a user's allergies and diet, and a weekly meal plan execution validated against their calorie target. The starter ships it as a working example, and the [tutorial](https://upsidelab.io/suvereo/docs/customization/tutorial) builds it step by step, from the entities to the execution. The [evaluation guide](https://upsidelab.io/suvereo/docs/evaluate/getting-started) then tests it.
- **E-commerce** - [Enthusiast](https://upsidelab.io/tools/enthusiast) is the domain definition for online stores, with integrations for store platforms and agents for product search, order intake and catalog enrichment.

The [plugins page](https://upsidelab.io/suvereo/plugins) lists everything ready to install.

## Documentation

| Topic | Where |
|---|---|
| Install and run Suvereo | [Getting started](https://upsidelab.io/suvereo/docs/getting-started/installation) |
| Build agents, tools and prompts | [Agents](https://upsidelab.io/suvereo/docs/agents/agent-architecture) |
| Add a domain, integrations and entities | [Customization](https://upsidelab.io/suvereo/docs/customization/domain-onboarding) and the [tutorial](https://upsidelab.io/suvereo/docs/customization/tutorial) |
| Test agents across models and prompts | [Evaluate](https://upsidelab.io/suvereo/docs/evaluate/getting-started) |

## Developing Suvereo

This repository holds the framework itself:

| Directory | Contents |
|---|---|
| `server/` | Django backend: REST API, Celery workers, WebSocket conversations |
| `frontend/` | React and TypeScript management panel |
| `plugins/` | Core plugins: `suvereo-common` contracts, model providers, the MCP integration and the tool-calling agent |
| `docs/` | The documentation site |
| `adrs/` | Architectural decision records |

To run it from source, create `server/.env` from `server/sample.env`, then start PostgreSQL with pgvector, Redis, the API, the worker and the frontend:

```shell
docker compose -f docker-compose.development.yml up
```

The API runs at [http://localhost:10000](http://localhost:10000) and the management panel at [http://localhost:10001](http://localhost:10001). To run the server without Docker, follow [server/README.md](server/README.md). [AGENTS.md](AGENTS.md), with one each in `server/`, `frontend/` and `plugins/suvereo-common/`, describes the layout, the commands and the conventions.

## License

Suvereo is a fully open-source agentic AI framework that will always remain free under the [MIT License](https://github.com/upsidelab/suvereo/blob/main/LICENSE.md).
