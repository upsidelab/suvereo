# Suvereo

Suvereo is an open-source AI framework built to make onboarding LLM agents into a system easy. It provides RAG, workflow orchestration and integrations with external systems.

The core is domain-agnostic and defines no domain entities of its own. It runs standalone, where you can still define your own agents and integrations. A domain vertical can be installed on top to supply domain entities (e.g. products and documents) along with agents and integrations for that domain.

## Layout

```
server/       Django backend (API, Celery, WebSocket) — see server/AGENTS.md
frontend/     React + TypeScript UI — see frontend/AGENTS.md
plugins/      Core plugins: suvereo-common contracts, LLM providers, MCP integration, tool-calling agent
docs/         Documentation site (Next.js)
specs/        Design specs, written before implementation
adrs/         Architectural decision records — the why behind intentional design
```

Docker: `docker-compose.yml` (production), `docker-compose.development.yml` (development; postgres with pgvector, redis, api, frontend, worker, beat).

Each plugin under `plugins/` is a standalone Poetry package. Contracts shared by all of them live in `plugins/suvereo-common` — see its `AGENTS.md`.

## Concepts

- **Data set** — the unit that scopes everything else: it owns agents and integrations, carries the language model and embedding configuration used for its content, and is the boundary for data-set-scoped permissions. One data set may be a whole company's content or a part of it, such as a brand or department.
- **Role** — a named set of permissions. Global roles apply across the whole system; data-set roles apply within one data set. A role is assigned directly or through groups, to users and service accounts alike.
- **Group** — a bucket of users and service accounts, used to assign roles to many of them at once.
- **Admin** — a built-in set of users, separate from roles and groups, that cannot be deleted. Admins hold all permissions, including ones added in the future. Only an admin can create, assign, deactivate or update another admin.
- **Service account** — an identity for authorizing programmatic API access with an API key instead of a login. Authorized through roles, like a user.
- **Agent** — a configured instance of an agent type (provided by a plugin) within a data set: name, description and type-specific config.
- **Conversation** — an interactive exchange between a user and an agent, streamed over WebSocket.
- **Agentic execution** — an autonomous, API-triggered batch run of an agent with structured input and result, no user in the loop. Runs in the background and is tracked through `pending`, `in_progress`, and `finished` or `failed`. An agent plugin can offer several execution definitions, selected by `execution_key`.
- **Integration** — a configured connection to an external system on a data set. Its type comes from a plugin, which defines the settings stored in its config.
- **Entity** — a domain object supplied by a vertical, persisted by core and listed in the UI (see Verticals).
- **Vertical** — a plugin that adds a domain to the core by defining its entities (see Verticals).

## Verticals

A vertical adds a domain to the core. It is a Django app (a plugin) enabled through `INSTALLED_VERTICALS` in the instance configuration (`server/pecl/settings_override.py`). Its main purpose is to:

- define domain-specific entities (models and migrations), which are registered in core and persisted in the database;
- define how those entities are handled, e.g. entity retrievers that agent tools use.

Domain-specific agents and tools are built on top of the vertical, either as separate plugins or directly in the vertical's own codebase, so a vertical need not be a set of plugins. It can be installed from PyPI or maintained in-tree (e.g. in a fork).

## Rules

- Pre-commit runs ruff and the frontend lint.
- Role names are area-nouns ("Management", never "Managers"). People-nouns belong to Groups.
- A change that adds or removes an app, plugin or top-level directory must update the relevant `AGENTS.md`.
