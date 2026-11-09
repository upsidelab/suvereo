# The Integrations

The domain definition can store recipes and profiles, but nothing fills the tables. This page adds the [integrations](/docs/concepts#integration) that do. It defines two integration types, a recipe source and a user source, the managers that store what they fetch, and a sample integration of each type. The concepts are covered in [Integrations](/docs/customization/integrations), and the part of a domain definition that defines them in [Domain definitions](/docs/customization/domain-definitions#4-integration-types).

An integration type is split in two. The **type** states what a source of recipes must provide, and the **manager** turns what it provides into entities. Integrations only implement the type, so a new source of recipes, such as a food blog or a meal-kit service, is one new class and no change to the code that stores recipes.

New files on this page:

```
diet_domain/
├── structures.py        # extended
├── classification.py    # allergens and dietary tags from ingredients
├── sync/
│   ├── __init__.py
│   ├── recipe.py
│   └── user.py
├── integrations.py      # the two integration types
└── sources/
    ├── __init__.py
    ├── sample_recipe_source.py
    └── sample_user_source.py
```

## 1. The data that sources return

A source returns plain objects, not Django models. The manager decides how they are stored, so a source needs no knowledge of the database. Add them to `structures.py`, below the enums:

```python
from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class RecipeDetails:
    external_id: str
    title: str
    meal_type: MealType
    instructions: str
    servings: int
    ingredients: list[str]
    calories: float


@dataclass(frozen=True)
class ProfileDetails:
    allergies: list[Allergen] = field(default_factory=list)
    conditions: list[str] = field(default_factory=list)
    dietary_preferences: list[str] = field(default_factory=list)
    disliked_foods: list[str] = field(default_factory=list)
    target_calories: Optional[int] = None


@dataclass(frozen=True)
class UserDetails:
    email: str
    first_name: str
    last_name: str
    password: str
    profile: ProfileDetails
```

Move the imports to the top of the file. `calories` is per serving.

### Allergens and dietary tags

When a recipe is imported, the domain definition computes its allergens and dietary tags from its ingredients, since these fields drive the retriever and the validator. This is domain code that Suvereo knows nothing about: a source could supply the labels itself, and the domain definition could compute them any other way. In this tutorial a classifier does it with keyword lists, in `classification.py`. It is small:

```python
# diet_domain/classification.py
import re
from dataclasses import dataclass

from diet_domain.structures import Allergen, DietaryTag

# Heuristic keywords for matching ingredient names. The lists are short and can be extended.
ALLERGEN_KEYWORDS: dict[Allergen, tuple[str, ...]] = {
    Allergen.GLUTEN: ("wheat", "flour", "bread", "pasta", "spaghetti", "noodle", "barley", "couscous", "tortilla"),
    Allergen.DAIRY: ("milk", "cheese", "butter", "cream", "yogurt", "parmesan", "mozzarella", "feta"),
    Allergen.EGGS: ("egg", "mayonnaise"),
    Allergen.PEANUTS: ("peanut",),
    Allergen.TREE_NUTS: ("almond", "walnut", "cashew", "pecan", "hazelnut", "pistachio"),
    Allergen.SOY: ("soy", "tofu", "edamame", "miso"),
    Allergen.FISH: ("fish", "salmon", "tuna", "cod", "anchovy", "anchovies", "mackerel"),
    Allergen.SHELLFISH: ("prawn", "shrimp", "crab", "lobster", "mussel", "clam", "oyster"),
    Allergen.SESAME: ("sesame", "tahini"),
}

MEAT_KEYWORDS = ("chicken", "beef", "pork", "lamb", "bacon", "ham", "sausage", "turkey", "duck", "mince")


@dataclass(frozen=True)
class Classification:
    allergens: list[Allergen]
    dietary_tags: list[DietaryTag]


class IngredientClassifier:
    def __init__(self) -> None:
        self._allergen_patterns = {
            allergen: self._compile(keywords) for allergen, keywords in ALLERGEN_KEYWORDS.items()
        }
        self._meat_pattern = self._compile(MEAT_KEYWORDS)

    def classify(self, ingredient_names: list[str]) -> Classification:
        names = [name.lower() for name in ingredient_names]
        allergens = [
            allergen
            for allergen, pattern in self._allergen_patterns.items()
            if any(pattern.search(name) for name in names)
        ]
        contains_meat = any(self._meat_pattern.search(name) for name in names)
        vegetarian = not contains_meat and Allergen.FISH not in allergens and Allergen.SHELLFISH not in allergens
        vegan = vegetarian and Allergen.DAIRY not in allergens and Allergen.EGGS not in allergens
        dietary_tags = [
            tag for tag, applies in ((DietaryTag.VEGETARIAN, vegetarian), (DietaryTag.VEGAN, vegan)) if applies
        ]
        return Classification(allergens=allergens, dietary_tags=dietary_tags)

    @staticmethod
    def _compile(keywords: tuple[str, ...]) -> re.Pattern:
        alternatives = "|".join(re.escape(keyword) for keyword in keywords)
        return re.compile(rf"\b(?:{alternatives})(?:e?s)?\b")
```

The keywords are keyed by `Allergen`, and the classifier returns enum members. The sync stores them as plain strings. A keyword match is a heuristic. It can label a dish wrongly, as the check at the end of this page shows. A domain definition whose output people rely on for their health would need a better source of this information.

## 2. The managers

A manager subclasses `BaseSourceIntegrationManager`. It receives an integration, calls `fetch()` and stores the result. Suvereo calls `sync(plugin, dataset_id, integration_id)` when a sync of an integration of the type is started, and gives the manager an indexer as `self._indexer`.

```python
# diet_domain/sync/recipe.py
from typing import TYPE_CHECKING

from suvereo_common.indexing import BaseEntityIndexer
from suvereo_common.integrations import BaseSourceIntegrationManager

from diet_domain.classification import IngredientClassifier
from diet_domain.models import Recipe

if TYPE_CHECKING:
    from diet_domain.integrations import RecipeSourcePlugin


class RecipeSourceManager(BaseSourceIntegrationManager):
    def __init__(self, indexer: BaseEntityIndexer):
        super().__init__(indexer)
        self._classifier = IngredientClassifier()

    def sync(self, plugin: "RecipeSourcePlugin", dataset_id: int, integration_id: int) -> None:
        for details in plugin.fetch():
            classification = self._classifier.classify(details.ingredients)
            recipe, _ = Recipe.objects.update_or_create(
                dataset_id=dataset_id,
                external_id=details.external_id,
                defaults={
                    "integration_id": integration_id,
                    "title": details.title,
                    "meal_type": details.meal_type.value,
                    "instructions": details.instructions,
                    "servings": details.servings,
                    "ingredients": details.ingredients,
                    "allergens": classification.allergens,
                    "dietary_tags": classification.dietary_tags,
                    "calories": details.calories,
                },
            )
            self._indexer.index(recipe)
```

- `update_or_create` on `(dataset, external_id)` makes a sync repeatable. Running it again updates the recipes that exist and adds the new ones.
- `self._indexer.index(recipe)` is what makes the recipe searchable. It calls `get_indexable_content()` of the recipe, embeds the text and stores the chunks, as described on the [previous page](/docs/customization/tutorial/domain-definition#3-making-the-recipe-searchable).

The user manager does more than store a record. A person in the diet domain definition is a Suvereo user, so the manager creates the account if it does not exist and grants the user the starter role that allows talking to agents:

```python
# diet_domain/sync/user.py
from dataclasses import asdict
from typing import TYPE_CHECKING

from django.apps import apps
from django.contrib.auth import get_user_model
from suvereo_common.integrations import BaseSourceIntegrationManager

from diet_domain.models import UserProfile

if TYPE_CHECKING:
    from diet_domain.integrations import UserSourcePlugin

CONVERSING_ROLE_NAME = "Agent Interaction"


class UserSourceManager(BaseSourceIntegrationManager):
    def sync(self, plugin: "UserSourcePlugin", dataset_id: int, integration_id: int) -> None:
        user_model = get_user_model()
        for details in plugin.fetch():
            user = user_model.objects.filter(email=details.email).first()
            if user is None:
                user = user_model.objects.create_user(
                    email=details.email,
                    password=details.password,
                    first_name=details.first_name,
                    last_name=details.last_name,
                )
            self._grant_conversing_role(user)
            UserProfile.objects.update_or_create(
                user=user,
                defaults={"dataset_id": dataset_id, "integration_id": integration_id, **asdict(details.profile)},
            )

    @staticmethod
    def _grant_conversing_role(user) -> None:
        global_role_model = apps.get_model("account", "GlobalRole")
        role = global_role_model.objects.filter(name=CONVERSING_ROLE_NAME).first()
        if role is not None:
            role.members.add(user)
```

- An existing user keeps their password. The password in `details` is used only when the account is created.
- The domain definition looks up the `account` app's model by name, through `apps.get_model`, rather than importing it, since a domain definition does not depend on the server's code.
- **Agent Interaction** is one of the starter roles created by `./manage.py seedroles`. If the role does not exist, the user is created without it, and an admin can assign a role in the UI. See [Users](/docs/management/users).

Export the managers:

```python
# diet_domain/sync/__init__.py
from .recipe import RecipeSourceManager
from .user import UserSourceManager

__all__ = ["RecipeSourceManager", "UserSourceManager"]
```

The managers refer to the integration types only in annotations, under `TYPE_CHECKING`, because the types in the next step import the managers.

## 3. The integration types

Each type subclasses `BaseIntegration`, points at its manager with `INTEGRATION_MANAGER` and declares the method its integrations implement. The names `fetch`, `RecipeDetails` and `UserDetails` belong to this domain definition. Suvereo does not define them.

```python
# diet_domain/integrations.py
from abc import ABC, abstractmethod
from collections.abc import Iterable

from suvereo_common.integrations import BaseIntegration

from diet_domain.structures import RecipeDetails, UserDetails
from diet_domain.sync import RecipeSourceManager, UserSourceManager


class RecipeSourcePlugin(BaseIntegration, ABC):
    INTEGRATION_MANAGER = RecipeSourceManager
    INTEGRATION_TYPE_NAME = "Recipe source"

    @abstractmethod
    def fetch(self) -> Iterable[RecipeDetails]: ...


class UserSourcePlugin(BaseIntegration, ABC):
    INTEGRATION_MANAGER = UserSourceManager
    INTEGRATION_TYPE_NAME = "User source"

    @abstractmethod
    def fetch(self) -> Iterable[UserDetails]: ...
```

- `INTEGRATION_TYPE_NAME` is the name shown in the UI. Each distinct name becomes an entry in the **Add integration** menu of a data set.
- `INTEGRATION_MANAGER` is the manager class itself. When a sync starts, Suvereo looks in `CATALOG_INTEGRATION_MANAGERS` for a class that is a subclass of it, which the registered manager is. A type can point at an abstract manager instead, which lets other packages implement the type without depending on the manager's code. A domain definition that keeps both in one package does not need that extra class.

## 4. The sample integrations

An integration implements a type for one external system. The two samples return fixed data, so the tutorial runs without an account anywhere. Each declares a `TYPE`, which identifies it in stored data, and a `NAME`, which the UI shows:

```python
# diet_domain/sources/sample_recipe_source.py
from collections.abc import Iterable

from diet_domain.integrations import RecipeSourcePlugin
from diet_domain.structures import MealType, RecipeDetails

# (external id, title, meal type, calories per serving, ingredients)
SAMPLE_RECIPES = [
    ("b1", "Oatmeal with berries", MealType.BREAKFAST, 320, ["rolled oats", "milk", "blueberries", "honey"]),
    ("b2", "Vegan chia pudding", MealType.BREAKFAST, 280, ["chia seeds", "oat drink", "maple syrup", "strawberries"]),
    ("b3", "Scrambled eggs on toast", MealType.BREAKFAST, 410, ["eggs", "bread", "butter", "chives"]),
    ("m1", "Chicken and rice bowl", MealType.MAIN, 620, ["chicken breast", "rice", "broccoli", "olive oil"]),
    ("m2", "Peanut noodles", MealType.MAIN, 580, ["wheat noodles", "peanut butter", "soy sauce", "carrot", "lime"]),
    ("m3", "Lentil and spinach curry", MealType.MAIN, 540, ["red lentils", "spinach", "chopped tomatoes", "onion"]),
    ("m4", "Baked salmon with potatoes", MealType.MAIN, 690, ["salmon fillet", "potatoes", "lemon", "olive oil"]),
    ("s1", "Hummus with carrot sticks", MealType.SNACK, 180, ["chickpeas", "tahini", "lemon", "carrot"]),
    ("s2", "Greek yogurt with walnuts", MealType.SNACK, 230, ["greek yogurt", "walnuts", "honey"]),
]


class SampleRecipeSource(RecipeSourcePlugin):
    TYPE = "sample-diet-recipes"
    NAME = "Sample recipes"

    def fetch(self) -> Iterable[RecipeDetails]:
        for external_id, title, meal_type, calories, ingredients in SAMPLE_RECIPES:
            yield RecipeDetails(
                external_id=external_id,
                title=title,
                meal_type=meal_type,
                instructions="",
                servings=1,
                ingredients=ingredients,
                calories=calories,
            )
```

```python
# diet_domain/sources/sample_user_source.py
from collections.abc import Iterable

from diet_domain.integrations import UserSourcePlugin
from diet_domain.structures import Allergen, ProfileDetails, UserDetails

SAMPLE_PASSWORD = "test123"

SAMPLE_USERS = [
    (
        "anna.kowalska@example.com",
        "Anna",
        "Kowalska",
        ProfileDetails(
            allergies=[Allergen.PEANUTS],
            conditions=["type 2 diabetes"],
            dietary_preferences=["low carb"],
            disliked_foods=["mushrooms"],
            target_calories=1700,
        ),
    ),
    (
        "piotr.nowak@example.com",
        "Piotr",
        "Nowak",
        ProfileDetails(dietary_preferences=["vegan"], disliked_foods=["cilantro"], target_calories=2900),
    ),
    (
        "maria.wisniewska@example.com",
        "Maria",
        "Wisniewska",
        ProfileDetails(
            allergies=[Allergen.GLUTEN, Allergen.DAIRY], conditions=["celiac disease"], target_calories=2100
        ),
    ),
]


class SampleUserSource(UserSourcePlugin):
    TYPE = "sample-diet-users"
    NAME = "Sample diet users"

    def fetch(self) -> Iterable[UserDetails]:
        for email, first_name, last_name, profile in SAMPLE_USERS:
            yield UserDetails(
                email=email, first_name=first_name, last_name=last_name, password=SAMPLE_PASSWORD, profile=profile
            )
```

```python
# diet_domain/sources/__init__.py
from .sample_recipe_source import SampleRecipeSource
from .sample_user_source import SampleUserSource

__all__ = ["SampleRecipeSource", "SampleUserSource"]
```

Every sample user gets the password `test123`. Use the samples only on an instance that is not exposed to other people.

## 5. Register the integrations

Integrations and managers are listed in `server/config/settings_override.py`. Types are not listed, since Suvereo finds them through the integrations that subclass them:

```python
CATALOG_INTEGRATION_PLUGINS = [
    "diet_domain.sources.SampleRecipeSource",
    "diet_domain.sources.SampleUserSource",
]
CATALOG_INTEGRATION_MANAGERS = [
    "diet_domain.sync.RecipeSourceManager",
    "diet_domain.sync.UserSourceManager",
]
```

Rebuild and restart with `docker compose up -d --build`.

## Try it

1. Open your data set and go to **Integrations**.
2. Choose **Add integration**. The menu lists the two types, **Recipe source** and **User source**. Choose **Recipe source** and then **Sample recipes**.
3. Click the **Synchronize data** button next to the new integration. The sync runs in the worker, and it needs the embedding provider of the data set, since each recipe is embedded.
4. Repeat for **User source** and **Sample diet users**.
5. Open **Recipes** and **User profiles** in the **Catalog** section of the sidebar. The recipes are listed with their calories and the allergens that the classifier found, and the three profiles with their allergies and targets.

Look at the allergens of "Peanut noodles": `gluten`, `dairy`, `peanuts` and `soy`. The `dairy` comes from "peanut butter", which the keyword `butter` matches. This is the limit of a keyword heuristic, and the reason the classifier is a separate class that can be replaced.

Running the sync again does not duplicate anything.

## Connecting a real system

The samples return fixed data. An integration for a real system differs in two ways: it has settings that an admin enters in the UI, and `fetch()` calls the system. This section adds one: recipes from [TheMealDB](https://www.themealdb.com/api.php), a public recipe API. TheMealDB does not state calories or servings, so the integration looks calories up in the USDA [FoodData Central](https://fdc.nal.usda.gov/) database, which needs a free API key, and estimates the servings from the weight of the ingredients.

Nothing else in the domain definition changes. The integration yields `RecipeDetails`, and the recipe manager from step 2 stores it as it stored the sample recipes.

New files:

```
diet_domain/sources/
├── measures.py
├── usda.py
└── mealdb_recipe_source.py
```

### Settings

The settings are a Pydantic model that subclasses `RequiredFieldsModel`, set as `CONFIGURATION_ARGS` of the integration. Its fields become the form shown when the integration is added, and the entered values are available as `self.CONFIGURATION_ARGS`. This integration has two. The USDA key is required. The TheMealDB key defaults to `1`, the free test key that TheMealDB publishes and that works for this tutorial. An admin who has their own key from TheMealDB can enter it in the form instead.

### Measures

TheMealDB lists ingredients with free-text measures, such as `1 1/2 cups` or `200g`. To weigh them, convert a measure to grams:

```python
# diet_domain/sources/measures.py
import re
from fractions import Fraction
from typing import Optional

QUANTITY_PATTERN = re.compile(r"^\s*(\d+\s+\d+/\d+|\d+/\d+|\d+(?:\.\d+)?)\s*([a-zA-Z]*)")

GRAMS_PER_UNIT: dict[str, float] = {
    "g": 1,
    "gram": 1,
    "grams": 1,
    "kg": 1000,
    "kilo": 1000,
    "mg": 0.001,
    "ml": 1,
    "l": 1000,
    "litre": 1000,
    "liter": 1000,
    "cl": 10,
    "dl": 100,
    "cup": 240,
    "cups": 240,
    "tbsp": 15,
    "tbs": 15,
    "tblsp": 15,
    "tablespoon": 15,
    "tablespoons": 15,
    "tsp": 5,
    "teaspoon": 5,
    "teaspoons": 5,
    "oz": 28.35,
    "ounce": 28.35,
    "ounces": 28.35,
    "lb": 453.6,
    "lbs": 453.6,
    "pound": 453.6,
    "pounds": 453.6,
    "pinch": 0.4,
    "dash": 0.6,
    "handful": 30,
    "slice": 30,
    "slices": 30,
    "clove": 5,
    "cloves": 5,
    "can": 400,
    "cans": 400,
    "tin": 400,
    "tins": 400,
}

DEFAULT_PIECE_GRAMS = 60.0


def parse_quantity(text: str) -> Optional[float]:
    try:
        return float(sum(Fraction(part) for part in text.split()))
    except (ValueError, ZeroDivisionError):
        return None


def measure_to_grams(measure: str) -> Optional[float]:
    match = QUANTITY_PATTERN.match(measure)
    if match is None:
        return None
    quantity = parse_quantity(match.group(1))
    if quantity is None:
        return None
    unit = match.group(2).lower()
    return quantity * GRAMS_PER_UNIT.get(unit, DEFAULT_PIECE_GRAMS)
```

A measure without a quantity, such as `to taste`, gives `None`, and the ingredient is left out of the calorie sum.

### Nutrition lookup

A small client asks FoodData Central for the energy of an ingredient per 100 g. It caches answers, since the same ingredients recur across recipes, and returns `None` when the lookup fails, so that one failed request skips an ingredient and not the whole sync:

```python
# diet_domain/sources/usda.py
import logging
from typing import Optional

import requests

logger = logging.getLogger(__name__)

SEARCH_URL = "https://api.nal.usda.gov/fdc/v1/foods/search"
REQUEST_TIMEOUT_SECONDS = 20
# FoodData Central nutrient numbers for energy in kcal: 208 is the standard one, 957 and 958 are calculated
# with Atwater factors. A food reports whichever applies, so the first one present is used.
ENERGY_NUTRIENT_NUMBERS = ("208", "957", "958")


class FoodDataCentralClient:
    def __init__(self, api_key: str):
        self._api_key = api_key
        self._cache: dict[str, Optional[float]] = {}

    def calories_per_100g(self, ingredient_name: str) -> Optional[float]:
        key = ingredient_name.strip().lower()
        if key not in self._cache:
            self._cache[key] = self._lookup(key)
        return self._cache[key]

    def _lookup(self, query: str) -> Optional[float]:
        try:
            response = requests.get(
                SEARCH_URL,
                params={"query": query, "dataType": "Foundation,SR Legacy", "pageSize": 1, "api_key": self._api_key},
                timeout=REQUEST_TIMEOUT_SECONDS,
            )
            response.raise_for_status()
            foods = response.json().get("foods", [])
        except (requests.RequestException, ValueError):
            logger.warning("FoodData Central lookup failed for '%s'", query, exc_info=True)
            return None
        return self._calories(foods[0].get("foodNutrients", [])) if foods else None

    @staticmethod
    def _calories(food_nutrients: list[dict]) -> Optional[float]:
        values = {nutrient.get("nutrientNumber"): nutrient.get("value") for nutrient in food_nutrients}
        return next((values[number] for number in ENERGY_NUTRIENT_NUMBERS if values.get(number) is not None), None)
```

### The integration

`fetch()` walks TheMealDB letter by letter, maps its categories to the meal types and turns each meal into `RecipeDetails`. It stops when it has returned `max_recipes` recipes, 50 by default:

```python
# diet_domain/sources/mealdb_recipe_source.py
import logging
import string
from collections.abc import Iterable
from typing import Optional

import requests
from pydantic import Field
from suvereo_common.utils import RequiredFieldsModel

from diet_domain.integrations import RecipeSourcePlugin
from diet_domain.sources.measures import measure_to_grams
from diet_domain.sources.usda import FoodDataCentralClient
from diet_domain.structures import MealType, RecipeDetails

logger = logging.getLogger(__name__)

MEALDB_SEARCH_URL = "https://www.themealdb.com/api/json/v1/{api_key}/search.php"
REQUEST_TIMEOUT_SECONDS = 20
# TheMealDB lists up to 20 ingredient fields per meal.
MAX_INGREDIENTS_PER_MEAL = 20
# The share of ingredients whose calories must be known. Below it, the recipe's total would be misleading.
MIN_RESOLVED_INGREDIENTS_RATIO = 0.75

# Recipes in other TheMealDB categories (desserts, sauces) are skipped.
MEAL_TYPES = {
    "Breakfast": MealType.BREAKFAST,
    "Starter": MealType.SNACK,
    "Side": MealType.SNACK,
    **{
        category: MealType.MAIN
        for category in ("Beef", "Chicken", "Goat", "Lamb", "Pasta", "Pork", "Seafood", "Vegan", "Vegetarian")
    },
}

# TheMealDB does not state how many people a recipe serves, so it is estimated from the weight of the ingredients.
PORTION_GRAMS = {MealType.BREAKFAST: 300, MealType.MAIN: 450, MealType.SNACK: 150}
# Upper limit of the estimate, so that a recipe of a few kilos is not read as dozens of servings.
MAX_SERVINGS = 12


class MealDbRecipeSourceConfig(RequiredFieldsModel):
    mealdb_api_key: str = Field(
        default="1",
        title="TheMealDB API key",
        description='The free test key "1" works. A key from https://www.themealdb.com/api.php can be used instead.',
    )
    usda_api_key: str = Field(
        title="USDA API key",
        description="FoodData Central API key, free at https://fdc.nal.usda.gov/api-key-signup",
    )
    max_recipes: int = Field(
        default=50,
        ge=1,
        title="Maximum recipes",
        description="The sync stops after this many recipes. Each ingredient needs a USDA request, so fewer is quicker.",
    )


class MealDbRecipeSource(RecipeSourcePlugin):
    TYPE = "mealdb-recipes"
    NAME = "TheMealDB recipes with USDA nutrition"
    CONFIGURATION_ARGS = MealDbRecipeSourceConfig

    def fetch(self) -> Iterable[RecipeDetails]:
        usda = FoodDataCentralClient(self.CONFIGURATION_ARGS.usda_api_key)
        fetched = 0
        for meal in self._meals(self.CONFIGURATION_ARGS.mealdb_api_key):
            meal_type = MEAL_TYPES.get(meal.get("strCategory"))
            if meal_type is None:
                continue
            recipe = self._to_recipe(meal, meal_type, usda)
            if recipe is not None:
                yield recipe
                fetched += 1
                if fetched >= self.CONFIGURATION_ARGS.max_recipes:
                    return

    @staticmethod
    def _meals(api_key: str) -> Iterable[dict]:
        # TheMealDB has no "list all meals" endpoint. Searching by first letter is the documented way to walk
        # the catalogue.
        for letter in string.ascii_lowercase:
            response = requests.get(
                MEALDB_SEARCH_URL.format(api_key=api_key), params={"f": letter}, timeout=REQUEST_TIMEOUT_SECONDS
            )
            response.raise_for_status()
            yield from response.json().get("meals") or []

    @staticmethod
    def _to_recipe(meal: dict, meal_type: MealType, usda: FoodDataCentralClient) -> Optional[RecipeDetails]:
        ingredients = []
        total_grams = total_calories = 0.0
        resolved = 0
        for index in range(1, MAX_INGREDIENTS_PER_MEAL + 1):
            name = (meal.get(f"strIngredient{index}") or "").strip()
            if not name:
                continue
            ingredients.append(name)
            grams = measure_to_grams(meal.get(f"strMeasure{index}") or "")
            calories_per_100g = usda.calories_per_100g(name) if grams is not None else None
            if calories_per_100g is None:
                continue
            total_grams += grams
            total_calories += calories_per_100g * grams / 100
            resolved += 1

        if not ingredients or resolved < MIN_RESOLVED_INGREDIENTS_RATIO * len(ingredients):
            logger.info("Skipping '%s': too few ingredients with known calories", meal["strMeal"])
            return None
        servings = min(MAX_SERVINGS, max(1, round(total_grams / PORTION_GRAMS[meal_type])))
        calories = round(total_calories / servings)

        return RecipeDetails(
            external_id=meal["idMeal"],
            title=meal["strMeal"],
            meal_type=meal_type,
            instructions=meal.get("strInstructions") or "",
            servings=servings,
            ingredients=ingredients,
            calories=calories,
        )
```

- **Categories.** `MEAL_TYPES` maps TheMealDB categories to `MealType`. Desserts and other categories are not in the map, so they are skipped.
- **Calories.** The calories of a recipe are the sum over its ingredients of `calories per 100 g × grams / 100`. A recipe is skipped when fewer than 75% of its ingredients could be resolved.
- **Servings.** The number of servings is the total weight divided by a typical portion for the meal type, between 1 and `MAX_SERVINGS`. Calories per serving follow from it.

These are choices of this integration, not of Suvereo. A source that gets servings and nutrition from its API would be much shorter.

Export it next to the samples, in `sources/__init__.py`:

```python
from .mealdb_recipe_source import MealDbRecipeSource
from .sample_recipe_source import SampleRecipeSource
from .sample_user_source import SampleUserSource

__all__ = ["MealDbRecipeSource", "SampleRecipeSource", "SampleUserSource"]
```

### Register and use it

```python
CATALOG_INTEGRATION_PLUGINS = [
    "diet_domain.sources.MealDbRecipeSource",
    "diet_domain.sources.SampleRecipeSource",
    "diet_domain.sources.SampleUserSource",
]
```

Rebuild and restart with `docker compose up -d --build`, then add a **Recipe source** in the UI and choose **TheMealDB recipes with USDA nutrition**. The form has the TheMealDB key, already filled with `1`, and the maximum number of recipes, already filled with `50`, and asks for the USDA API key, which you can get at [fdc.nal.usda.gov/api-key-signup](https://fdc.nal.usda.gov/api-key-signup). Start the sync as before. It makes a request for each distinct ingredient, so it takes a few minutes, and more if you raise the maximum. The `requests` dependency is already declared in the package's `pyproject.toml`.

Several connections of one integration can exist on a data set by default. Set `ALLOWS_MULTIPLE_INSTANCES = False` on an integration that makes sense only once.

Continue with [the agent](/docs/customization/tutorial/agent).
