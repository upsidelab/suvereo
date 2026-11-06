# Domain definitions

A [domain definition](/docs/concepts#domain-definition) brings a [domain](/docs/concepts#domain) to Suvereo: the records it works with, the external systems it relies on and the way both reach [agents](/docs/concepts#agent). Once a domain definition is installed, Suvereo stores its data, lists it in the UI, indexes it for search and makes it available to every agent built on the domain definition. See [Domain onboarding](/docs/customization/domain-onboarding) for how the pieces fit together.

## Implementation

A domain definition is a Django app. It is enabled in the instance settings, and it can contain any of the parts below. The code on this page uses a hypothetical example, a domain definition for articles, to show what each part looks like. Each part is optional: a domain definition whose agents never search its data needs no retriever, injector or builder.

| Part | What it does |
|---|---|
| [Entities](#1-entities) | The Django models of the domain. Suvereo lists them in the UI and indexes their content. |
| [Retrievers](#2-retrievers) | Search the domain definition's entities by meaning. |
| [Injector and builder](#3-injector-and-builder) | Hand the retrievers to agents and their tools. |
| [Integration types](#4-integration-types) | Sync entities in from external systems, or let agents act in them. |

The app can ship as a standalone package, with its own `pyproject.toml` that depends on `suvereo-common`, `django` and `pgvector`, or live as a plain Django app inside a codebase that the server can already import, such as a fork. The steps below are the same for both, except where they say otherwise.

```
articles_domain/
├── __init__.py
├── apps.py
├── models/            # one module per entity, re-exported in __init__.py
├── migrations/
├── retrievers/        # when tools search the entities
├── injector.py        # when tools search the entities
├── builder.py         # when tools search the entities
└── sync/              # when entities are synced from external systems
```

A domain definition depends on `suvereo-common` and not on the server code. It references the server's models by string, for example `"catalog.DataSet"`.

### 1. Entities

An entity is a Django model that mixes in `DomainEntity` and declares an inner `EntityMeta`. Suvereo reads `EntityMeta` to list the entity in the UI as a read-only table, so the entity needs no serializer, view or frontend code.

```python
from django.db import models
from suvereo_common.entities import DomainEntity, EntityField


class Article(DomainEntity, models.Model):
    dataset = models.ForeignKey("catalog.DataSet", on_delete=models.CASCADE, related_name="articles")
    integration = models.ForeignKey(
        "catalog.Integration", on_delete=models.CASCADE, related_name="articles", null=True, blank=True
    )
    external_id = models.CharField(max_length=255)
    title = models.CharField(max_length=1024)
    content = models.TextField()

    class Meta:
        constraints = [models.UniqueConstraint(fields=["dataset", "external_id"], name="uq_articles_article")]

    class EntityMeta:
        slug = "articles"
        label = "Articles"
        list_fields = [EntityField("title"), EntityField("external_id", label="ID")]

    def get_indexable_content(self) -> str:
        return f"{self.title}\n{self.content}"
```

| `EntityMeta` field | Description |
|---|---|
| `slug` | The URL-safe identifier of the entity. |
| `label` | The plural name shown in the UI. |
| `list_fields` | The columns of the table, as `EntityField(name, label=None)`. The label defaults to the field name. |

Entities usually belong to a [data set](/docs/concepts#data-set), through a `dataset` foreign key. An entity that is synced from an [integration](/docs/concepts#integration) can also reference it. A unique constraint over the natural key within a data set keeps repeated syncs from creating duplicates.

#### Making an entity searchable

To let agents search an entity by meaning, add a chunk model. A chunk is one piece of the entity's content together with its embedding. It subclasses `BaseEmbeddingChunk`, which provides the `content` and `embedding` fields, and points at the entity with a foreign key named `chunks` on the entity's side:

```python
from django.db import models
from suvereo_common.indexing import BaseEmbeddingChunk


class ArticleChunk(BaseEmbeddingChunk):
    article = models.ForeignKey("articles_domain.Article", on_delete=models.CASCADE, related_name="chunks")
```

The indexer that Suvereo provides takes any entity with a `dataset`, a `chunks` relation and a `get_indexable_content()` method. It splits the returned text into pieces, embeds them with the embedding model of the data set and replaces the entity's chunks. Entities that agents never search need neither the chunk model nor `get_indexable_content()`.

### 2. Retrievers

A retriever is what a tool calls to search an entity. For vector search, subclass `BaseVectorStoreRetriever` and declare what is searchable:

```python
from suvereo_common.retrievers import BaseVectorStoreRetriever

from articles_domain.models import ArticleChunk


class ArticleRetriever(BaseVectorStoreRetriever[ArticleChunk]):
    chunk_model = ArticleChunk
    dataset_filter = "article__dataset_id"
```

`chunk_model` is the chunk table to query, and `dataset_filter` is the lookup path from a chunk to the id of its data set, so that a search stays within one data set. The base class embeds the query with the data set's embedding model and returns the closest chunks through `find_content_matching_query(query)`. A retriever can override that method to add its own strategy, such as an extra filter before ranking. For retrieval that is not vector search, subclass `BaseRetriever`.

### 3. Injector and builder

Tools reach retrievers through the [injector](/docs/agents/injector), and the [builder](/docs/agents/builder) creates the injector. To expose a domain definition's retrievers, subclass `Injector` and `AgentBuilder`:

```python
from suvereo_common.injectors import Injector


class ArticlesInjector(Injector):
    def __init__(self, *args, article_retriever: ArticleRetriever, **kwargs):
        super().__init__(*args, **kwargs)
        self._article_retriever = article_retriever

    @property
    def article_retriever(self) -> ArticleRetriever:
        return self._article_retriever
```

```python
from suvereo_common.builder import AgentBuilder
from suvereo_common.config import AgentConfig


class ArticlesAgentBuilder(AgentBuilder[AgentConfig]):
    def _build_injector(self) -> ArticlesInjector:
        chat_history = self._build_chat_history()
        return ArticlesInjector(
            article_retriever=ArticleRetriever(
                data_set_id=self._data_set_id,
                embeddings_registry=self._embeddings_registry,
                searcher=self._config.similarity_searcher(),
            ),
            repositories=self._repositories,
            chat_history=chat_history,
            memory_compactor=self._build_memory_compactor(chat_history),
            tool_scratchpad=self._tool_scratchpad,
        )
```

An agent opts in by setting `BUILDER_CLASS = ArticlesAgentBuilder`, and its tools then read `self._injector.article_retriever`. Agents that leave `BUILDER_CLASS` unset use the default builder and do not see the domain definition's retrievers. See [Agent Classes](/docs/agents/agent-classes).

### 4. Integration types

A domain definition can define the kinds of external systems it relies on, as [integration types](/docs/customization/integrations#integration-types-and-integrations). A type can serve two purposes: bringing entities in, or letting agents act in the system. A type that brings entities in is made of two classes:

- A **manager**, which subclasses `BaseSourceIntegrationManager` and implements `sync(plugin, dataset_id, integration_id)`. It reads from a plugin and stores entities. Suvereo gives it an indexer as `self._indexer`, and the manager calls `self._indexer.index(entity)` for every entity that needs to be searchable.
- The **integration type**, which subclasses `BaseIntegration`, points at the manager through `INTEGRATION_MANAGER` and declares what an integration of that type provides. The integrations, one per external system, subclass it. They are covered in [Integrations](/docs/customization/integrations).

```python
from abc import ABC, abstractmethod
from collections.abc import Iterable

from suvereo_common.integrations import BaseIntegration, BaseSourceIntegrationManager


class BaseArticleSourceManager(BaseSourceIntegrationManager, ABC):
    pass


class ArticleSourcePlugin(BaseIntegration, ABC):
    INTEGRATION_MANAGER = BaseArticleSourceManager
    INTEGRATION_TYPE_NAME = "Article source"

    @abstractmethod
    def fetch(self) -> Iterable[ArticleDetails]: ...


class ArticleSourceManager(BaseArticleSourceManager):
    def sync(self, plugin: ArticleSourcePlugin, dataset_id: int, integration_id: int) -> None:
        for details in plugin.fetch():
            entity, _ = Article.objects.update_or_create(
                dataset_id=dataset_id,
                external_id=details.external_id,
                defaults={"integration_id": integration_id, "title": details.title, "content": details.content},
            )
            self._indexer.index(entity)
```

Suvereo finds the manager of an integration by looking in `CATALOG_INTEGRATION_MANAGERS` for the class that is a subclass of the type's `INTEGRATION_MANAGER`. Integrations in other packages depend on the type and the abstract manager. When several packages are going to implement them, these two can live in a small shared package instead of the domain definition.

A type for acting in a system needs only the type class. It declares the actions as methods and has no manager, since nothing is synced. The builder resolves the integration that is configured on the data set and the injector exposes it to tools. See [Letting agents act](/docs/customization/integrations#letting-agents-act).

### 5. Registration

The domain definition is registered in `server/pecl/settings_override.py`:

```python
INSTALLED_DOMAIN_DEFINITIONS = ["articles_domain"]
CATALOG_ENTITY_PLUGINS = ["articles_domain.models.Article"]
CATALOG_INTEGRATION_MANAGERS = ["articles_domain.sync.ArticleSourceManager"]
CATALOG_INTEGRATION_PLUGINS = ["wiki_integration.WikiSource"]
```

| Setting | Lists |
|---|---|
| `INSTALLED_DOMAIN_DEFINITIONS` | The domain definition's Django apps. Suvereo adds them to `INSTALLED_APPS`. |
| `CATALOG_ENTITY_PLUGINS` | The entity models to list in the UI. |
| `CATALOG_INTEGRATION_MANAGERS` | The managers of the domain definition's integration types. |
| `CATALOG_INTEGRATION_PLUGINS` | The integrations that can be connected to a data set. |

A standalone package must also be installed into the environment of the server, for example with `pip install -e ./articles-domain definition`, a path dependency or from PyPI. A domain definition that lives in the codebase is importable already.

### 6. Migrations

Django only sees an app that is in `INSTALLED_APPS`, so register the domain definition first and then generate the migrations from the `server/` directory:

```bash
./manage.py makemigrations articles_domain
./manage.py migrate
```

Django writes the migrations into the app's own `migrations/` directory. For a standalone package that works when the package is installed in editable mode, so that the app directory is the source directory. A package that cannot be installed that way needs its migration files written by hand, following what `makemigrations` would produce.

Agents are then built on top of the domain definition, and they can use the retrievers it exposes. See [Agent Classes](/docs/agents/agent-classes).
