---
name: add-vertical
description: Scaffold a new Suvereo vertical — a Django app with domain entities (models, migrations), retrievers, builder/injector and integration managers — and register it in settings. Use when asked to add, create or build a new vertical or domain.
---

# Add a vertical

A vertical adds a domain to the domain-agnostic core. It is a Django app enabled through `INSTALLED_VERTICALS` in `server/pecl/settings_override.py`. Its job: define domain entities (models and migrations, persisted by core and listed in the UI) and how they are handled (retrievers that agent tools use, integration managers that sync data in). 
There are two ways to ship it; core prescribes neither:
- **Standalone package** — its own installable package (own `pyproject.toml`), e.g. published to PyPI or kept in its own repository.
- **In the codebase** — a plain Django app living directly in a codebase that is already importable by the server (e.g. in-tree in a fork). No packaging, no install step.

Sections marked *(standalone package only)* are skipped for in-codebase verticals. Everything else applies to both.

Where to look in this repo:
- Contracts: `plugins/suvereo-common/` (`entities`, `indexing`, `retrievers`, `injectors`, `builder`, `integrations`) — read its `AGENTS.md`.
- How core loads a vertical: `server/catalog/entities/registry.py` (entities), `server/catalog/integrations/registry/manager.py` (integration managers), `INSTALLED_VERTICALS` handling in `server/pecl/settings.py`.

## 1. Settle the design first

Ask only what the code cannot tell you:
- Domain name (drives the app name `<domain>_vertical`).
- The entities and their fields, and which of them need vector search (those get an embedding chunk model).
- Where data comes from: which integration types will sync it, or is that out of scope for now?
- Do agent tools need domain retrievers? (Then you need an injector and a builder.)
- Where it lives: a standalone package (its own repository / PyPI), or directly in a codebase (which one).

## 2. Layout

The Django app has the same contents in both cases:

```
<domain>_vertical/
  __init__.py
  apps.py
  models/            # one module per entity, re-exported in __init__.py
  migrations/
  retrievers/        # only if tools need them
  builder.py         # only with retrievers
  injector.py        # only with retrievers
  sync/              # only with integration managers
```

- **In the codebase:** put `<domain>_vertical/` inside the target codebase, so it is importable as `<domain>_vertical` (or under that codebase's import path, adjusting the dotted paths below). Do not add the packaging files.
- **Standalone package:** wrap it with the packaging files:

```
<domain>-vertical/
  pyproject.toml
  README.md
  <domain>_vertical/   # the app above
```

### Packaging *(standalone package only)*

`pyproject.toml` (Poetry): depends on `django`, `pgvector` (for vector search) and `suvereo-common`. Take version ranges from `plugins/suvereo-common/pyproject.toml` and `server/pyproject.toml`.

### App config

`apps.py`:

```python
from django.apps import AppConfig


class <Domain>VerticalConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "<domain>_vertical"
    verbose_name = "<Domain> Vertical"
```

## 3. Entities (`models/`)

```python
from django.db import models
from suvereo_common.entities import DomainEntity, EntityField


class <Entity>(DomainEntity, models.Model):
    dataset = models.ForeignKey("catalog.DataSet", on_delete=models.CASCADE, related_name="<entities>")
    integration = models.ForeignKey(
        "catalog.Integration", on_delete=models.CASCADE, related_name="<entities>", null=True, blank=True
    )
    external_id = models.CharField(max_length=255)
    title = models.CharField(max_length=1024)
    content = models.TextField()

    class Meta:
        constraints = [models.UniqueConstraint(fields=["dataset", "external_id"], name="uq_<domain>_<entity>")]

    class EntityMeta:
        slug = "<entities>"
        label = "<Entities>"
        list_fields = [EntityField("title"), EntityField("external_id", label="ID")]

    def get_indexable_content(self) -> str:
        return f"{self.title}\n{self.content}"
```

- Everything is scoped to a data set (`dataset` FK); `integration` is only needed when entities are synced from one.
- Add a `UniqueConstraint` over the natural key within a data set.
- `EntityMeta` (`slug`, `label`, `list_fields`) is all core needs to render the entity as a read-only table through the API and UI: it builds the serializer from `list_fields`, so no view or frontend work is required.
- `get_indexable_content()` only for entities that get embedded.

Vector-searchable entities get a chunk model, subclassing `BaseEmbeddingChunk` (which provides `content` and `embedding`):

```python
from django.db import models
from suvereo_common.indexing import BaseEmbeddingChunk


class <Entity>Chunk(BaseEmbeddingChunk):
    <entity> = models.ForeignKey("<domain>_vertical.<Entity>", on_delete=models.CASCADE, related_name="chunks")
```

Reference other apps' models by string (`"catalog.DataSet"`); never import server code. A vertical depends on `suvereo-common`, not on the server. Re-export models in `models/__init__.py`.

## 4. Retrievers, injector, builder (only if tools need them)

Retriever (vector search): declare what is searchable, the base class does the rest.

```python
from suvereo_common.retrievers import BaseVectorStoreRetriever

from <domain>_vertical.models import <Entity>Chunk


class <Entity>Retriever(BaseVectorStoreRetriever[<Entity>Chunk]):
    chunk_model = <Entity>Chunk
    dataset_filter = "<entity>__dataset_id"
```

`dataset_filter` is the lookup path from a chunk to its data set id. For non-vector retrieval subclass `BaseRetriever`.

Injector: extend the framework `Injector` with the retrievers.

```python
from suvereo_common.injectors import Injector


class <Domain>Injector(Injector):
    def __init__(self, *args, <entity>_retriever: <Entity>Retriever, **kwargs):
        super().__init__(*args, **kwargs)
        self._<entity>_retriever = <entity>_retriever

    @property
    def <entity>_retriever(self) -> <Entity>Retriever:
        return self._<entity>_retriever
```

Builder: subclass `AgentBuilder` and override `_build_injector()`. Mirror the default `AgentBuilder._build_injector` in `plugins/suvereo-common/suvereo_common/builder/default.py` and add your retrievers; `self._data_set_id`, `self._embeddings_registry` and `self._config.similarity_searcher()` are available when building them.

```python
class <Domain>AgentBuilder(AgentBuilder[AgentConfig]):
    def _build_injector(self) -> <Domain>Injector:
        ...
```

Agents then set `BUILDER_CLASS = <Domain>AgentBuilder` on the agent class (see the `add-agent` skill), and tools read `self._injector.<entity>_retriever`.

## 5. Integration managers (only if data is synced in)

An integration category is a manager class subclassing `BaseSourceIntegrationManager` (`suvereo_common.integrations`). Source integration plugins point at it through `INTEGRATION_MANAGER`; the server resolves the concrete manager registered in `CATALOG_INTEGRATION_MANAGERS` that is a subclass of that class.

```python
from abc import ABC, abstractmethod
from collections.abc import Iterable

from suvereo_common.integrations import BaseIntegration, BaseSourceIntegrationManager


class Base<Entity>SourceManager(BaseSourceIntegrationManager, ABC):
    pass


class <Entity>SourcePlugin(BaseIntegration, ABC):
    INTEGRATION_MANAGER = Base<Entity>SourceManager
    INTEGRATION_TYPE_NAME = "<Entity> source"

    @abstractmethod
    def fetch(self) -> Iterable[<Entity>Details]: ...


class <Entity>SourceManager(Base<Entity>SourceManager):
    def sync(self, plugin: <Entity>SourcePlugin, dataset_id: int, integration_id: int) -> None:
        for details in plugin.fetch():
            entity, _ = <Entity>.objects.update_or_create(
                dataset_id=dataset_id,
                external_id=details.external_id,
                defaults={"integration_id": integration_id, "title": details.title, "content": details.content},
            )
            self._indexer.index(entity)
```

The plugin ABCs and the abstract manager are what third-party source plugins depend on, so when several packages will implement them, put these in a small shared package instead of the vertical itself. The framework injects `self._indexer`; call it for every embedded entity.

## 6. Register

In `server/pecl/settings_override.py`:

```python
INSTALLED_VERTICALS = ["<domain>_vertical"]
CATALOG_ENTITY_PLUGINS = ["<domain>_vertical.models.<Entity>"]
CATALOG_INTEGRATION_MANAGERS = ["<domain>_vertical.sync.<Entity>SourceManager"]
CATALOG_INTEGRATION_PLUGINS = [...]  # concrete source plugins, if any
```

`INSTALLED_VERTICALS` is merged into `INSTALLED_APPS`. In-codebase verticals are importable already. *(standalone package only)* Install the package into the server's environment (`pip install -e <dir>` or a path dependency, or from PyPI).

## 7. Migrations

The vertical must be registered first: `makemigrations` only sees apps in `INSTALLED_APPS`. Generate with `./manage.py makemigrations <domain>_vertical` from `server/` and review the output. **Never run `migrate`**; the user does that.

Django writes migrations into the app's own directory (`<domain>_vertical/migrations/`). For a standalone package this works only when it is installed as editable, so that the app directory is the source directory. If the package cannot be installed as editable, `makemigrations` would write into `site-packages`; instead write the migration files by hand in the package's `migrations/` directory, following what `makemigrations` would produce for the models.

## 8. Checks

- Test retriever, sync and model logic next to the app (or the host codebase's own test location); pytest-django and model-bakery (see `server/AGENTS.md`).
- Run `ruff check` and `ruff format` on the new code.
- No docstrings or comments on implementations (conventions in `server/AGENTS.md`).
- If the change adds a top-level directory (a standalone package in this repo does), update the relevant `AGENTS.md`.
