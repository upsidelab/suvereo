# Integrations

An [integration](/docs/concepts#integration) connects a [data set](/docs/concepts#data-set) to an external system. It can bring content in from the system, let [agents](/docs/concepts#agent) act in it, or both. Acting can mean calling the system's API from a tool, or handing the agent a set of ready-made tools, such as those of an MCP server. Suvereo stores the settings of each connection, shows them as a form in the UI and creates the integration when it is needed, so the class you write only describes the system and what it offers. The code on this page uses a hypothetical example, a wiki that stores articles, to show what each kind of integration looks like.

## Implementation

### Integration types and integrations

Integrations are written on two levels:

- An **integration type** is an intermediate class. It subclasses `BaseIntegration` from `suvereo_common.integrations` and defines what every integration of that type can do, such as the methods an agent's tool calls or the data a sync reads. It does not talk to any system itself.
- An **integration** is a class that subclasses an integration type and implements it for one external system. It is the class that is registered, and each connection configured on a data set is an instance of it.

Defining a type is a recommendation rather than a requirement, since an integration can subclass `BaseIntegration` directly. A type is worth the extra class because it separates what is needed from where it comes from:

- **A shared interface.** Integrations of one type have the same methods in code and differ only in the external system behind them. A tool, a manager or a builder depends on the type, so it works with any integration of it. Adding support for another system means adding one more integration, with no change to the code that uses it.
- **Lookup by type.** Suvereo finds the integrations of a data set by their type. A vertical's builder, for example, resolves the one that is connected to the data set (see [Letting agents act](#letting-agents-act)).
- **Grouping in the UI.** Integrations are grouped by the `INTEGRATION_TYPE_NAME` of their type. Each distinct name is an entry in the menu for adding an integration, the dialog offers the integrations of that type, and each connected integration is labelled with it.

A type is usually defined by a [vertical](/docs/customization/verticals#4-integration-types), together with the manager that handles it. Suvereo defines a base type for tool-providing integrations (see [Giving agents ready-made tools](#giving-agents-ready-made-tools)), and an integration plugin can define a type of its own.

### Declaring an integration

The class variables are split between the two levels. A type declares what is common, and an integration declares what is specific to its system:

| Variable | Declared by | Description |
|---|---|---|
| `INTEGRATION_TYPE_NAME` | The type | The name of the type, shown in the UI. Defaults to `"Basic integration"`. |
| `INTEGRATION_MANAGER` | The type | The manager class, for types that sync content in. `None` by default. |
| `TYPE` | The integration | A stable identifier of the integration. It is stored with each connection, so it should not change after release. |
| `NAME` | The integration | The name shown in the UI. |
| `CONFIGURATION_ARGS` | The integration | A subclass of `RequiredFieldsModel` that defines the settings. Its fields become the form in the UI. `None` for an integration that needs no settings. |
| `ALLOWS_MULTIPLE_INSTANCES` | Either | Whether a data set can hold more than one connection of the integration. `True` by default. An integration that makes sense only once per data set sets it to `False`. |

The values entered in the UI are available on the instance as `self.CONFIGURATION_ARGS.base_url`. A data set can hold several connections of an integration by default, so it can override `instance_name()` to return a label that tells them apart. It otherwise returns `NAME` for every one of them.

An external system and an integration do not have to match one to one. Several integrations can talk to the same system, each implementing a different type, and they can share the settings model. In the examples below, one wiki is available both as a source of articles and as a place to publish them. Each is connected separately, so a data set can use the wiki for one purpose and not the other:

```python
from pydantic import Field
from suvereo_common.utils import RequiredFieldsModel


class WikiConfig(RequiredFieldsModel):
    base_url: str = Field(title="Base URL", description="Base URL of the API")
    api_key: str = Field(title="API key", description="Key used to authenticate")
```

### Syncing content in

An integration type for syncing content in points at an integration manager, which is the class that stores what the integrations fetch and is covered with the [vertical](/docs/customization/verticals#4-integration-types). The type declares the manager in `INTEGRATION_MANAGER` and the method that integrations implement:

```python
from abc import ABC, abstractmethod
from collections.abc import Iterable

from suvereo_common.integrations import BaseIntegration


class ArticleSourcePlugin(BaseIntegration, ABC):
    INTEGRATION_MANAGER = BaseArticleSourceManager
    INTEGRATION_TYPE_NAME = "Article source"

    @abstractmethod
    def fetch(self) -> Iterable[ArticleDetails]: ...
```

The method names and the data they return are defined by the type, not by Suvereo. When a sync is started, Suvereo finds the manager of the type, which is the registered subclass of `INTEGRATION_MANAGER`, and calls its `sync()` with the integration. The manager calls `fetch()` and stores the result.

An integration for a system implements the type:

```python
class WikiSource(ArticleSourcePlugin):
    TYPE = "wiki_articles"
    NAME = "Wiki articles"
    CONFIGURATION_ARGS = WikiConfig

    def fetch(self) -> Iterable[ArticleDetails]:
        client = WikiClient(self.CONFIGURATION_ARGS.base_url, self.CONFIGURATION_ARGS.api_key)
        return [ArticleDetails(...) for item in client.list_articles()]
```

### Letting agents act

An integration can let agents act in an external system, such as creating a record or sending a request through its API. For this, the type declares the actions as methods, and each integration implements them for its system. The type has no `INTEGRATION_MANAGER`, since nothing is synced:

```python
class ArticlePublisherPlugin(BaseIntegration, ABC):
    INTEGRATION_TYPE_NAME = "Article publisher"

    @abstractmethod
    def publish_article(self, title: str, body: str) -> str: ...


class WikiPublisher(ArticlePublisherPlugin):
    TYPE = "wiki_publisher"
    NAME = "Wiki publisher"
    CONFIGURATION_ARGS = WikiConfig

    def publish_article(self, title: str, body: str) -> str:
        client = WikiClient(self.CONFIGURATION_ARGS.base_url, self.CONFIGURATION_ARGS.api_key)
        return client.publish(title, body)
```

The integration is made available to agents through the injector. The vertical's [builder](/docs/agents/builder) asks the integration plugin resolver for the integration of that type that is configured on the data set, and its [injector](/docs/agents/injector) exposes it:

```python
class ArticlesAgentBuilder(AgentBuilder[AgentConfig]):
    def _build_injector(self) -> ArticlesInjector:
        resolver = self._config.integration_plugin_resolver()
        return ArticlesInjector(
            article_publisher=resolver.resolve(self._data_set_id, ArticlePublisherPlugin),
            ...
        )
```

`resolve()` returns the configured integration of that type, or `None` when the data set has none. When several are connected, it returns the one added last. A vertical that needs to provide several of them can extend the server's resolver, which the agent configuration sets as `integration_plugin_resolver`. A tool then calls the integration through the injector. It depends on `ArticlePublisherPlugin` and does not know which system is behind it:

```python
def run(self, title: str, body: str) -> str:
    return self._injector.article_publisher.publish_article(title, body)
```

Switching a data set to another system is then a matter of connecting another integration of the same type.

### Giving agents ready-made tools

`BaseToolProvidingIntegration` is an integration type defined by Suvereo. An integration that subclasses it hands agents tools that already exist, without writing them as tools of the agent. It implements `get_tools()`, an async method that returns the LangChain tools the integration currently offers:

```python
from langchain_core.tools import BaseTool
from suvereo_common.integrations import BaseToolProvidingIntegration


class WikiToolsIntegration(BaseToolProvidingIntegration):
    TYPE = "wiki_tools"
    NAME = "Wiki Tools"
    INTEGRATION_TYPE_NAME = "Tool Provider"
    CONFIGURATION_ARGS = WikiConfig

    async def get_tools(self) -> list[BaseTool]:
        return await fetch_wiki_tools(self.CONFIGURATION_ARGS.base_url)
```

Unlike an integration that agents act through, a tool provider needs nothing in the builder or the injector, and agents do not need to know that it exists. When an agent is built for a conversation, the builder asks every tool-providing integration connected to the data set for its tools and attaches them to the agent. An integration that fails or takes longer than ten seconds to answer contributes no tools for that turn, and the others are unaffected. A tool whose name is already taken, by the agent's own tools or by an integration resolved earlier, is dropped with a warning. Agents built on `BaseToolCallingAgent` pick the tools up, as they can answer asynchronously. See [Tools](/docs/agents/tools#tools-from-integrations).

Suvereo ships one tool provider, for MCP servers, in the `suvereo-integration-mcp` package. It is registered in the same way as a custom integration.

### OAuth

An integration whose credentials come from an OAuth authorization-code flow also subclasses `BaseOAuthIntegration`. It names the settings field that identifies what is being authorized with `OAUTH_FIELD`, and the field that holds the renewal credential with `OAUTH_REFRESH_FIELD`. It implements three class methods:

- `oauth_start(target, redirect_uri, client)` starts the flow and returns the URL to send the user to.
- `oauth_exchange_code(pending, code)` exchanges the authorization code for credentials, returned as settings fields to merge into the form.
- `oauth_refresh(config)` renews stored credentials and raises `OAuthError` when they cannot be renewed.

An instance can persist credentials it renews on its own, such as during a conversation, through the writer that Suvereo gives it with `set_config_writer()`. `MCPServerIntegration` combines `BaseToolProvidingIntegration` and `BaseOAuthIntegration`.

### Registration

An integration is enabled by listing its dotted path in `server/pecl/settings_override.py`. Types are not listed, since they are found through the integrations that subclass them:

```python
CATALOG_INTEGRATION_PLUGINS = [
    "wiki_integration.WikiSource",
    "wiki_integration.WikiPublisher",
    "wiki_integration.WikiToolsIntegration",
    "suvereo_integration_mcp.MCPServerIntegration",
]
```

The integration is then available when you add an integration to a data set in the UI. Packages outside the codebase must be installed into the environment of the server first. An integration that syncs content in also needs the manager of its type listed in `CATALOG_INTEGRATION_MANAGERS`, which the vertical does.
