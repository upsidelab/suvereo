# Mocks

[Agents](/docs/concepts#agent) reach external systems through [integrations](/docs/concepts#integration): a recipe source, a shop, a document store. During an evaluation, each integration the suite declares is replaced by a mock. A mock gives the agent two things:

- **Data**: in sandbox mode (`agent: {type: ...}`) the mock's data is synced into the throwaway [data set](/docs/concepts#data-set), the same way a real integration's sync fills a data set, so the agent searches a known set of records.
- **Calls**: methods the agent calls at runtime answer from the suite's YAML, and every call is recorded. Metrics such as `mock_calls` and `mock_called` then read those recorded calls.

A suite on an agent you configured needs no mocks for data its data set already holds. A sandbox suite, `agent: {type: ...}`, starts from an empty data set, so it needs a mock for each source of data the agent searches: for the tutorial's nutrition assistant, a recipe source that fills the catalog before the run starts.

## A mock integration for your domain definition

A suite names a mock integration in one line:

```yaml
integrations:
  - class: diet_domain.evaluation.RecipeMockIntegration
    config: {data: {recipes: recipes.yaml}}
```

```yaml
# recipes.yaml, next to suite.yaml; calories are per serving
- {id: b-chia, title: Vegan chia pudding, meal_type: breakfast, calories: 280, ingredients: [chia seeds, oat drink, maple syrup, strawberries]}
- {id: m-lentil, title: Lentil and spinach curry, meal_type: main, calories: 540, ingredients: [red lentils, spinach, chopped tomatoes, onion, vegetable stock]}
- {id: s-hummus, title: Hummus with carrot sticks, meal_type: snack, calories: 180, ingredients: [chickpeas, tahini, lemon, carrot]}
```

`recipes` is a YAML, JSON or CSV file relative to the suite, or an inline list. Each recipe needs `id`, `title`, `meal_type` (`breakfast`, `main` or `snack`), `calories` and `ingredients`; `servings` and `instructions` are optional. The sync works out allergens and the vegetarian and vegan tags from the ingredients, as for recipes from the tutorial's sample source.

The mock is two small files in a new `diet_domain/evaluation/` package of your [domain definition](/docs/concepts#domain-definition). The first validates a fixture record and turns it into the `RecipeDetails` the tutorial's sources return:

```python
# diet_domain/evaluation/fixture_recipe.py
from typing import Any

from pydantic import BaseModel, ConfigDict, ValidationError
from suvereo_common.evaluation.mocks import MockConfigError

from diet_domain.structures import MealType, RecipeDetails


class FixtureRecipe(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    title: str
    meal_type: MealType
    calories: float
    ingredients: list[str]
    servings: int = 1
    instructions: str = ""

    @classmethod
    def load_all(cls, records: list[dict[str, Any]]) -> list["FixtureRecipe"]:
        try:
            return [cls.model_validate(record) for record in records]
        except ValidationError as e:
            raise MockConfigError(f"Invalid fixture recipe: {e}") from e

    def to_recipe_details(self) -> RecipeDetails:
        return RecipeDetails(
            external_id=self.id,
            title=self.title,
            meal_type=self.meal_type,
            instructions=self.instructions,
            servings=self.servings,
            ingredients=self.ingredients,
            calories=self.calories,
        )
```

The second is the integration:

```python
# diet_domain/evaluation/recipe_mock_integration.py
from functools import cached_property

from suvereo_common.evaluation.mocks import BaseMockIntegration, FixtureRecords

from diet_domain.integrations import RecipeSourcePlugin
from diet_domain.structures import RecipeDetails

from .fixture_recipe import FixtureRecipe


class RecipeMockIntegration(BaseMockIntegration, RecipeSourcePlugin):
    TYPE = "mock_recipes"
    NAME = "Mock recipe source"

    @classmethod
    def mock_classes(cls) -> tuple:
        return ()

    def fetch(self) -> list[RecipeDetails]:
        self._check_behaviour()
        return [recipe.to_recipe_details() for recipe in self._recipes]

    @cached_property
    def _recipes(self) -> list[FixtureRecipe]:
        return FixtureRecipe.load_all(FixtureRecords.load(self.config.data.get("recipes"), self.base_dir))
```

```python
# diet_domain/evaluation/__init__.py
from .follows_diet import FollowsDiet
from .recipe_mock_integration import RecipeMockIntegration

__all__ = ["FollowsDiet", "RecipeMockIntegration"]
```

- **Both bases**: `BaseMockIntegration` makes it a mock a suite can name; `RecipeSourcePlugin` makes it a recipe source, so the sandbox syncs it through the tutorial's `RecipeSourceManager`, which classifies, stores and embeds each recipe.
- **`mock_classes`** lists the mocks of calls the integration answers at runtime. A recipe source answers none, so a suite that sets a `behaviour` on it gets an error naming the methods it mocks.
- **`FixtureRecords.load`** reads the `data` entry as a file relative to the suite (`self.base_dir`) or as an inline list. `FixtureRecipe` validates each record, so `validateeval` reports a recipe with a wrong `meal_type` before any run.
- **Registration**: the suite names the class by its dotted path, so it needs no entry in `CATALOG_INTEGRATION_PLUGINS`. The manager it syncs through, `RecipeSourceManager`, is registered already.

`follows_diet.py` holds the metric from [Metrics](./metrics#add-your-own-metric). A case can swap the recipes for its own, as `no-dairy-free-breakfast` does in [Suites and Cases](./suites#changing-a-metric-or-a-mock-for-one-case).

## Mocking the calls an agent makes

An integration the agent calls during a run, such as a shop it places orders in, is mocked call by call. The examples below come from [Enthusiast](https://upsidelab.io/tools/enthusiast), the e-commerce domain definition, whose order-intake agent places orders through an e-commerce connector.

### Behaviour

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

A case can override the suite's behaviour for a method; its `behaviour` replaces the suite's for that method.

### Three ways to build one

**1. YAML only.** Name the plugin interface and declare behaviours. Every method is generated from the interface; methods without a behaviour return `None`, or raise with `strict: true`.

```yaml
integrations:
  - interface: enthusiast_domain_common.interfaces.ECommerceIntegrationPlugin
    config:
      behaviour:
        create_order_with_items: {returns: "ORD-{n}"}
        get_admin_url_for_order_id: {returns: "https://shop.example/orders/{order_id}"}
```

Methods that build a component (`build_connector() -> ECommercePlatformConnector`) return a mock of that component, and the behaviour keys go to whichever mock has the method. A behaviour returns plain YAML values, so this suits methods that return text, numbers and mappings.

**2. A mock class for state.** When answers depend on earlier calls, subclass `BaseMock`. Declared behaviour still wins; `_answer_unmatched_call` answers every other call:

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

**3. A mock integration that does both.** Set `MOCK_CLASS` and return `self.mock` from the builder, and the same integration syncs data and answers calls. Enthusiast's `ECommerceMockIntegration` syncs a catalog for product search and answers orders:

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

## Ready-made mocks

Enthusiast, the e-commerce domain definition, ships these:

| Integration | Data | What it gives the agent |
|---|---|---|
| `enthusiast_domain_common.evaluation.ECommerceMockIntegration` | `catalog`: products (`sku` and `name` required) | The catalog synced for product search, and a shop connector with in-memory orders (`ORD-1`, `ORD-2`, …), stock and an admin URL. |
| `enthusiast_domain_common.evaluation.DocumentMockIntegration` | `documents`: records with `url`, `title` and `content` | The documents synced, with embeddings, for document search agents. |
