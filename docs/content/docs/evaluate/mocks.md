# Mocks

Agents reach external systems through integrations: an e-commerce connector, a product source, a document source. During an evaluation, each integration the suite declares is replaced by a mock that records every call and answers from the suite's YAML. Metrics such as `mock_calls` and `mock_called` then read those recorded calls.

In sandbox mode (`agent: {type: ...}`) a mock's data is also synced into the throwaway DataSet, the same way a real integration's sync fills a DataSet, so one declaration gives the agent both its searchable catalog and the system it writes to.

## Behaviour

Each mocked method takes one behaviour, or a list of them where the first that matches wins:

| Key | What the method does |
|---|---|
| `returns` | Returns the value. Strings are templates: `{n}` is the call number, and named arguments fill their own placeholders, e.g. `"ORD-{n}"` or `"{sku}"`. |
| `sequence` | Returns one value per call; the last one repeats. |
| `raises` | Raises `{error, message}`: an error the mock knows by name, a builtin such as `TimeoutError`, or a dotted class path. |
| `when` | Applies the behaviour only when these named arguments match, e.g. `when: {sku: MUG-RED}`. |
| `latency_ms` | Waits this long before answering. |

```yaml
behaviour:
  get_product_by_sku:
    - {when: {sku: MUG-RED}, raises: {error: TimeoutError, message: "Shop timed out"}}
    - {returns: null}
  create_order_with_items: {sequence: [ORD-100, ORD-101]}
```

A case can override the suite's behaviour for a method; see `po-out-of-stock` in the order-intake suite.

## Three ways to build a mock

### 1. YAML only

Name the plugin interface and declare behaviours. Every method is generated from the interface; methods without a behaviour return `None`, or raise with `strict: true`.

```yaml
integrations:
  - interface: enthusiast_ecommerce_common.interfaces.ECommerceIntegrationPlugin
    config:
      behaviour:
        create_order_with_items: {returns: "ORD-{n}"}
        get_admin_url_for_order_id: {returns: "https://shop.example/orders/{order_id}"}
```

Methods that build a component (`build_connector() -> ECommercePlatformConnector`) return a mock of that component, and the behaviour keys go to whichever mock has the method.

### 2. A mock class for state

When answers depend on earlier calls, subclass `BaseMock`. Declared behaviour still wins; `_answer_unmatched_call` answers every other call:

```python
from suvereo_common.evaluation.mocks import BaseMock


class CartConnectorMock(BaseMock):
    INTERFACE = ECommercePlatformConnector
    ERRORS = {"ECommerceConnectorError": ECommerceConnectorError}

    def _answer_unmatched_call(self, method, arguments):
        if method == "create_order_with_items":
            return f"ORD-{len(self.calls_to(method))}"
        return super()._answer_unmatched_call(method, arguments)
```

`ERRORS` lets suites raise the class by its short name. `self.data` holds the integration's `data`.

### 3. A mock integration your vertical ships

Wrap the mock in a `BaseMockIntegration` so suites name it in one line. The e-commerce vertical ships `ECommerceMockIntegration`:

```python
class ECommerceMockIntegration(BaseMockIntegration, ECommerceIntegrationPlugin):
    TYPE = "mock_ecommerce"
    NAME = "Mock e-commerce platform"
    MOCK_CLASS = ECommerceConnectorMock

    def build_connector(self) -> ECommercePlatformConnector:
        return self.mock

    def build_product_source(self) -> FixtureProductSource:
        return FixtureProductSource([p.to_product_details() for p in CatalogProduct.load_all(self._catalog)])
```

`self.mock` is the run's shared mock instance, so metrics read the same calls the agent made.

## Shipped mocks

| Integration | Data | What it gives the agent |
|---|---|---|
| `enthusiast_ecommerce_common.evaluation.ECommerceMockIntegration` | `catalog`: a YAML, JSON or CSV file, or an inline list of products (`sku` and `name` required; `description`, `price`, `stock` and more optional) | The catalog synced for product search, and a shop connector with in-memory orders (`ORD-1`, `ORD-2`, …), stock and an admin URL. Ordering an unknown SKU raises `ECommerceConnectorError`. |
| `enthusiast_ecommerce_common.evaluation.DocumentMockIntegration` | `documents`: records with `url`, `title` and `content` | The documents synced, with embeddings, for document search agents. |

```yaml
integrations:
  - class: enthusiast_ecommerce_common.evaluation.ECommerceMockIntegration
    config:
      data: {catalog: data/products.yaml}
      behaviour: {create_order_with_items: {raises: {error: ECommerceConnectorError, message: "Out of stock"}}}
```
