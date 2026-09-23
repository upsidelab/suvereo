# Building a Custom Integration

Custom integrations let you connect Enthusiast to systems that aren’t supported out of the box.

## Types of Integrations.

1. E-Commerce Integration - Enables bidirectional communication between agents and an e-commerce system.
2. Product Source Integration - Enables one-way fetching of product data from an e-commerce or PIM system.
3. Document Source Integration - Enables one-way fetching of documents such as manuals, FAQs, or internal content.
4. Language Model Integration - Connects agents to a language model provider.
5. Tool Providing Integration - Hands agents extra tools to call at runtime, such as the tools exposed by an MCP server.

## Building an E-Commerce Integration

An E-Commerce Integration enables bidirectional communication between Enthusiast AI Agents and an e-commerce platform.

To build one, implement the [enthusiast_common.interfaces.ECommerceIntegrationPlugin](https://github.com/upsidelab/enthusiast/blob/main/plugins/enthusiast-common/enthusiast_common/interfaces.py) interface.

Your integration class must define two static fields:
- `NAME` - The name shown to admins in the integrations list.
- `CONFIGURATION_ARGS` - A subclass of [enthusiast_common.utils.RequiredFieldsModel](https://github.com/upsidelab/enthusiast/blob/main/plugins/enthusiast-common/enthusiast_common/utils.py) defining the integration's configuration schema.

Your class must also implement the following methods:
- `build_connector(self)` - Returns an implementation of [enthusiast_common.connector.ECommercePlatformConnector](https://github.com/upsidelab/enthusiast/blob/main/plugins/enthusiast-common/enthusiast_common/connectors/ecommerce_platform_connector.py). This connector is available to agents at runtime.
- `build_product_source(self)` - Returns an implementation of [enthusiast_common.interfaces.ProductSourcePlugin](https://github.com/upsidelab/enthusiast/blob/main/plugins/enthusiast-common/enthusiast_common/interfaces.py), used to build a local product index.

### Example Implementation

```python
class UpCommerceIntegrationConfig(RequiredFieldsModel):
    base_url: str = Field(description="Base URL for the API")
    api_key: str = Field(description="API key for connecting to the E-Commerce platform")
    
class UpCommerceIntegration(ECommerceIntegrationPlugin):
    NAME = "UpCommerce"
    CONFIGURATION_ARGS = UpCommerceIntegrationConfig
    
    def build_connector(self) -> ECommercePlatformConnector:
        return UpCommercePlatformConnector(base_url=self.CONFIGURATION_ARGS.base_url,
                                           api_key=self.CONFIGURATION_ARGS.api_key)
                                           
   def build_product_source(self) -> ProductSourcePlugin:
        return UpCommerceProductSource(base_url=self.CONFIGURATION_ARGS.base_url,
                                       api_key=self.CONFIGURATION_ARGS.api_key)
                                       
class UpCommercePlatformConnector(ECommercePlatformConnector):
    def create_empty_order(self, email: Optional[str] = None, address: Optional[Address] = None) -> str:
        ...

    def add_to_order(self, order_id: str, sku: str, quantity: int) -> bool:
        ...

    def create_order_with_items(self, items: list[tuple[str, int]], email: Optional[str] = None, address: Optional[Address] = None) -> str:
        ...

    def get_product_by_sku(self, sku: str) -> ProductDetails:
        ...

    def create_product(self, product_details: ProductDetails) -> str:
        ...

    def update_product(self, sku: str, product_details: ProductDetails) -> bool:
        ...

    def get_admin_url_for_order_id(self, order_id: str) -> str:
        ...
    
class UpCommerceProductSource(ProductSourcePlugin):
    def fetch(self) -> list[ProductDetails]:
        return [ProductDetails( ... )]
```

## Building a Product Source Integration

A Product Source enables one-way fetching of product data from an e-commerce or PIM system. 

To build a product source, implement the [enthusiast_common.interfaces.ProductSourcePlugin](https://github.com/upsidelab/enthusiast/blob/main/plugins/enthusiast-common/enthusiast_common/interfaces.py) interface.

Your integration class must define the following static field:
- `CONFIGURATION_ARGS` - A subclass of [enthusiast_common.utils.RequiredFieldsModel](https://github.com/upsidelab/enthusiast/blob/main/plugins/enthusiast-common/enthusiast_common/utils.py) defining the integration's configuration schema.

It should also implement the following method:
- `fetch(self)` - Returns a list of [enthusiast_common.structures.ProductDetails](https://github.com/upsidelab/enthusiast/blob/main/plugins/enthusiast-common/enthusiast_common/structures.py). These products will be indexed in Enthusiast.

### Example Implementation

```python
class UpCommerceProductSource(ProductSourcePlugin):
    def fetch(self) -> list[ProductDetails]:
        return [ProductDetails( ... )]
```

## Building a Document Source Integration

A Document Source enables one-way fetching of documents such as manuals, FAQs, or internal content.

To build a document source, implement the [enthusiast_common.interfaces.DocumentSourcePlugin](https://github.com/upsidelab/enthusiast/blob/main/plugins/enthusiast-common/enthusiast_common/interfaces.py) interface.

Your integration class must define the following static field:
- `CONFIGURATION_ARGS` - A subclass of [enthusiast_common.utils.RequiredFieldsModel](https://github.com/upsidelab/enthusiast/blob/main/plugins/enthusiast-common/enthusiast_common/utils.py) defining the integration's configuration schema.

It should also implement the following method:
- `fetch(self)` - Returns a list of [enthusiast_common.structures.DocumentDetails](https://github.com/upsidelab/enthusiast/blob/main/plugins/enthusiast-common/enthusiast_common/structures.py). These documents will be indexed in Enthusiast.

### Example Implementation

```python
class UpCommerceDocumentSource(DocumentSourcePlugin):
    def fetch(self) -> list[DocumentDetails]:
        return [DocumentDetails( ... )]
```

## Connecting an MCP Server

Enthusiast ships an MCP (Model Context Protocol) integration in the `enthusiast-integration-mcp` package. Install it
and add `enthusiast_integration_mcp.MCPServerIntegration` to `CATALOG_INTEGRATION_PLUGINS` in your settings override.

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

No agent configuration is needed. Once a server is connected, the data set's agents pick up its tools on their next
conversation turn, as long as they can answer asynchronously - which every agent built on `BaseToolCallingAgent` can.
Data sets with no MCP server connected are untouched: Enthusiast checks for connected servers before doing any of the
extra work, so nothing changes for them.

## Building a Tool Providing Integration

MCP is one way to hand agents extra tools, but it isn't the only one. To expose tools from any other system,
implement [enthusiast_common.integrations.BaseToolProvidingIntegration](https://github.com/upsidelab/enthusiast/blob/main/plugins/enthusiast-common/enthusiast_common/integrations/base.py).

Your integration class must define the same static fields as any other integration (`TYPE`, `NAME`,
`INTEGRATION_TYPE_NAME`, `CONFIGURATION_ARGS`), and implement one method:
- `get_tools(self)` - An async method returning the LangChain tools this integration currently makes available.

Set `ALLOWS_MULTIPLE_INSTANCES = True` if a data set should be allowed to hold more than one instance of your type.
Enthusiast discovers tool providers generically, so agents pick up your tools alongside any connected MCP servers
without knowing your integration exists.

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
