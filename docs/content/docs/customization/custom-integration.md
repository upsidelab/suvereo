# Building a Custom Integration

Custom integrations let you connect Suvereo to systems that aren’t supported out of the box.

## Types of Integrations

1. Language Model Integration - Connects agents to a language model provider.
2. Tool Providing Integration - Hands agents extra tools to call at runtime, such as the tools exposed by an MCP server.

A vertical adds its own integration types. Enthusiast, the e-commerce vertical, adds e-commerce, product source and
document source integrations; see [its guide](https://upsidelab.io/tools/enthusiast/docs/customization/custom-integration).

## Connecting an MCP Server

Suvereo ships an MCP (Model Context Protocol) integration in the `suvereo-integration-mcp` package. Install it
and add `suvereo_integration_mcp.MCPServerIntegration` to `CATALOG_INTEGRATION_PLUGINS` in your settings override.

Each connected server is a regular integration configured on a data set, with four configuration fields:
- `url` - Full URL of the MCP endpoint.
- `transport` - Either `http` (the default) or `sse` for older servers.
- `auth_token` - The full value of the auth header, scheme included, such as `Bearer abc123`. Leave it empty for a
  server that needs no authentication.
- `auth_header` - The header the token is sent in, `Authorization` by default. Set it to something like `X-API-Key`
  for servers that expect a raw key under their own header.

Credentials are two plain fields rather than a header mapping so the admin form, which renders one text input per
field, can express them. That covers the bearer and API-key schemes servers use in practice.

Connections are made with `langchain[mcp]`, whose `langchain.mcp` module is currently in beta - importing it emits a
`LangChainBetaWarning`. Client-side response caching is enabled, so a server that publishes a TTL hint has its tool
list served from cache rather than refetched on every conversation turn. Servers that publish no hint are simply
fetched as before.

Unlike other integration types, a data set may hold **any number** of MCP servers - the plugin opts into this by
declaring `ALLOWS_MULTIPLE_INSTANCES = True`. Connected servers are listed by host, so several of them stay
tellable apart.

Because tools are fetched while a user waits for a reply, servers are contacted concurrently and each one gets its
own short timeout. A server that is unreachable, mis-configured, or simply slow contributes no tools for that turn
and is logged; the rest are unaffected. Tool names have to be unique, so a tool whose name is already taken - by
one of the agent's own tools, or by a server connected ahead of it - is dropped with a warning rather than
silently shadowing the original.

Each agent selects the servers it uses under **Tool sources** in its settings; a newly connected server is
selected for no agent. An agent picks up the tools of its selected servers on its next conversation turn, as long as
it can answer asynchronously - which every agent built on `BaseToolCallingAgent` can.
Agents with no server selected are untouched: Suvereo checks for selected servers before doing any of the extra work,
so nothing changes for them.

## Building a Tool Providing Integration

MCP is one way to hand agents extra tools, but it isn't the only one. To expose tools from any other system,
implement [suvereo_common.integrations.BaseToolProvidingIntegration](https://github.com/upsidelab/suvereo/blob/main/plugins/suvereo-common/suvereo_common/integrations/base.py).

Your integration class must define the same static fields as any other integration (`TYPE`, `NAME`,
`INTEGRATION_TYPE_NAME`, `CONFIGURATION_ARGS`), and implement one method:
- `get_tools(self)` - An async method returning the LangChain tools this integration currently makes available.

Set `ALLOWS_MULTIPLE_INSTANCES = True` if a data set should be allowed to hold more than one instance of your type.
Suvereo discovers tool providers generically, so your integration shows up under **Tool sources** next to
connected MCP servers, and the agents that select it pick up its tools without knowing your integration exists.

### Example Implementation

```python
class UpCommerceToolsConfig(RequiredFieldsModel):
    base_url: str = Field(title="Base URL", description="Base URL for the API")

class UpCommerceToolsIntegration(BaseToolProvidingIntegration):
    TYPE = "upcommerce_tools"
    NAME = "UpCommerce Tools"
    INTEGRATION_TYPE_NAME = "Tool Provider"
    CONFIGURATION_ARGS = UpCommerceToolsConfig

    async def get_tools(self) -> list[BaseTool]:
        return await fetch_upcommerce_tools(self.CONFIGURATION_ARGS.base_url)
```
