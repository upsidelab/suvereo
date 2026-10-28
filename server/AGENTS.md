# Server

The backend of Suvereo: an API that serves agent configuration and conversations. It manages data sets, agents, integrations, users and permissions, runs agents (conversations stream over WebSocket) and handles background work such as indexing and file processing.

Django 5 + DRF + Celery + Channels. Run commands from `server/`.

## Commands

- Install: `poetry install` (CI uses `pyproject.dev.toml`, which installs `enthusiast-common` from `../plugins`; the default file uses the PyPI release)
- Run: `./manage.py runserver`; workers: `celery -A pecl.celery worker` and `celery -A pecl.celery beat`
- Tests: `pytest`, `pytest agent/tests/test_views.py`, `pytest agent/tests/test_views.py::TestClass::test_method` (needs Postgres with pgvector, see `sample.test.env`)
- Lint: `ruff check .` and `ruff format .`
- API docs: Swagger at `/api/docs/`

## Code structure

The codebase is modular and extensible. Core capabilities (LLM and embedding providers, integrations, agents) are opt-in plugins that the server discovers through registries and settings.

`plugins/enthusiast-common` is the source of truth for the interfaces. Both the server and every plugin depend on it. Anything meant to be an opt-in plugin defines its interface in `enthusiast-common`, so the server knows the contract, and the plugins provide the implementations. This is the recommended structure for all Enthusiast plugins.

In practice:

- The server depends on the abstract classes in `enthusiast-common`, never on a concrete plugin.
- A plugin depends on `enthusiast-common`, never on the server.
- A new kind of plugin starts with its interface (and registry base, if it needs one) in `enthusiast-common`, then a server-side registry that loads implementations from settings.

## Apps

- `account` — users, groups, roles, service accounts, JWT auth (access + refresh tokens), `account/authorization/` (permission codes and rules)
- `agent` — agents, conversations (`agent/conversation/`, `ConversationManager`), agentic execution (`agent/agentic_execution/`), task status (`agent/task_status/`), agent building and plugin registries (`agent/core/`), memory strategies (`agent/core/memory/`), file parsers
- `catalog` — data sets, integrations and their OAuth flow (`catalog/integrations/`), entities, indexing pipeline, retrieval; embeddings are stored with pgvector
- `pecl` — project settings, URL routing, Celery app
- `utils` — shared helpers (base registry, function helpers, serializers)

Apps expose their API under `/api/` and are mounted at the root in `pecl/urls.py`.

## Settings and plugins

`pecl/settings.py` holds defaults; `pecl/settings_override.py` holds the configuration of a concrete Suvereo instance. It is valid with no vertical configured. There you choose the LLM and embedding providers, agents and agentic executions, and, if used, verticals with their entities and the agents, integrations and integration managers built on top of them. Dotted paths in these settings are loaded through registries: `INSTALLED_VERTICALS` (merged into `INSTALLED_APPS`), `AVAILABLE_AGENTS`, `AVAILABLE_AGENTIC_EXECUTION_DEFINITIONS`, `CATALOG_LANGUAGE_MODEL_PROVIDERS`, `CATALOG_EMBEDDING_PROVIDERS`, `CATALOG_INTEGRATION_PLUGINS`, `CATALOG_INTEGRATION_MANAGERS`, `CATALOG_ENTITY_PLUGINS`, `FILE_PARSER_CLASSES`.

## Code conventions

- Code is validated with ruff.
- OOP-first: Favor object-oriented design — use classes, inheritance, and polymorphism. The codebase is built around abstract base classes and the plugin system relies on subclassing contracts in `enthusiast-common`.
- Annotate all function signatures and public attributes with types.
- Keep modules short, one concern each. Split views and serializers into packages once they grow.
- Use descriptive class and method names so comments are unnecessary. Comment only non-obvious or deliberately hacky code, briefly.
- Docstrings go on public interfaces only: `enthusiast-common` contracts and other APIs plugin authors build against. Implementations and server-internal code have none.
- Extend through the documented extension points (`enthusiast-common` base classes and registries) instead of adding new abstraction layers.

## Layout conventions

- A feature with its own mechanics (consumers, tasks, registries) is a sub-package with its own views, urls and serializers. Follow `agent/agentic_execution/`.
- Anything else is a flat module until it grows, then becomes a package with one module per resource, re-exported from `__init__.py`. Follow `account/views/`.
- Tests sit next to the code in `<app>/tests/` (or a sub-package's `tests/`).

## Authorization

Permissions are held by roles. A role is either global or scoped to a data set, and is assigned directly or through a group (a bucket of users and service accounts for role assignment), to users and service accounts alike.

Every API endpoint is authorized through `account.authorization`: `permission_classes = [IsAuthenticated]` plus a decorator such as `global_permission_required(PERMISSIONS.X.Y)`, or `enforce_dataset_scoped_permission` where the resource belongs to a data set. Never leave an endpoint open or guard it with ad-hoc checks such as role-name comparisons. Add new permission codes to `permission_codenames.py` and the rules, not inline.

Admins are users with `is_superuser=True`. This is not a role entity: it reuses Django's mechanism by which superusers hold every permission, so `has_perm` already passes for them and endpoints need no special case. `is_superuser` is still read occasionally in code (e.g. `admin_required`, or to widen what a list shows), but new endpoint authorization uses granular permissions, not `is_superuser`.

## Reference implementations

- Global-permission endpoint: `account/views/groups.py`
- Data-set-scoped endpoint: `agent/views.py`
- Endpoint tests: `account/tests/test_views/`, `agent/tests/test_views.py`

## Tests

pytest-django with model-bakery. Fixtures in `conftest.py`: `user`, `admin_user`, `api_client` (authenticated), `admin_api_client`, `data_set`, `conversation`, `temp_media_root`. Settings module is `pecl.settings` (`pytest.ini`).
