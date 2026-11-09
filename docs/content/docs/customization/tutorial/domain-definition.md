# The Domain Definition

This page gives the diet domain definition its data, and the way agents search it. It covers the entities, the retriever, the profile accessor, the injector and the builder, then registers the domain definition and creates its tables. Each part is described in [Domain definitions](/docs/customization/domain-definitions), and this page shows it for the diet domain.

Everything on this page is in the `diet_domain` package created in the [overview](/docs/customization/tutorial#create-the-package). The layout after this page:

```
diet_domain/
├── __init__.py
├── apps.py
├── structures.py
├── models/
│   ├── __init__.py
│   ├── recipe.py
│   ├── recipe_chunk.py
│   └── user_profile.py
├── retrievers/
│   ├── __init__.py
│   └── recipe.py
├── profiles.py
├── injector.py
├── builder.py
└── migrations/          # generated
```

## 1. The vocabulary

`structures.py` holds plain Python types that the rest of the domain definition shares. The values that the data can take are enums, so that code refers to `Allergen.PEANUTS` instead of repeating the string `"peanuts"`. The models store the plain strings, since an enum member of `StrEnum` is a string.

```python
from enum import StrEnum


class MealType(StrEnum):
    BREAKFAST = "breakfast"
    MAIN = "main"
    SNACK = "snack"

    @property
    def label(self) -> str:
        return "lunch or dinner" if self is MealType.MAIN else self.value


class Allergen(StrEnum):
    GLUTEN = "gluten"
    DAIRY = "dairy"
    EGGS = "eggs"
    PEANUTS = "peanuts"
    TREE_NUTS = "tree_nuts"
    SOY = "soy"
    FISH = "fish"
    SHELLFISH = "shellfish"
    SESAME = "sesame"


class DietaryTag(StrEnum):
    VEGETARIAN = "vegetarian"
    VEGAN = "vegan"
```

- `MealType` is one of three kinds of meal, which the entity stores, the search filters on and the meal plan uses. `MAIN` stands for lunch and dinner, which recipes do not distinguish. `label` is the wording that goes into the text that is indexed.
- `Allergen` is the vocabulary shared by the profile, the recipe and the search tool.
- `DietaryTag` is what a recipe can be labelled with. `StrEnum` needs Python 3.11, which is why the package declares `python = "^3.11"`.

## 2. The recipe entity

An [entity](/docs/customization/domain-definitions#1-entities) is a Django model that mixes in `DomainEntity` and declares `EntityMeta`. The recipe is the entity that agents search:

```python
# diet_domain/models/recipe.py
from django.db import models
from suvereo_common.entities import DomainEntity, EntityField

from diet_domain.structures import MealType


class Recipe(DomainEntity, models.Model):
    dataset = models.ForeignKey("catalog.DataSet", on_delete=models.CASCADE, related_name="recipes")
    integration = models.ForeignKey(
        "catalog.Integration", on_delete=models.CASCADE, related_name="recipes", null=True, blank=True
    )
    external_id = models.CharField(max_length=255)
    title = models.CharField(max_length=1024)
    meal_type = models.CharField(max_length=16, choices=[(meal_type.value, meal_type.label) for meal_type in MealType])
    instructions = models.TextField(blank=True)
    servings = models.PositiveSmallIntegerField(default=1)
    ingredients = models.JSONField(default=list)
    allergens = models.JSONField(default=list)
    dietary_tags = models.JSONField(default=list)
    calories = models.FloatField()

    class Meta:
        constraints = [models.UniqueConstraint(fields=["dataset", "external_id"], name="uq_diet_recipe")]

    class EntityMeta:
        slug = "recipes"
        label = "Recipes"
        list_fields = [
            EntityField("title"),
            EntityField("meal_type", label="Meal"),
            EntityField("calories", label="Calories per serving"),
            EntityField("allergens"),
        ]

    def get_indexable_content(self) -> str:
        ingredients = ", ".join(self.ingredients)
        tags = ", ".join(self.dietary_tags)
        meal = MealType(self.meal_type).label
        return f"{self.title}\nMeal: {meal}\nIngredients: {ingredients}\nDietary tags: {tags}\n{self.instructions}"

    def __str__(self) -> str:
        return self.title
```

What each part is for:

- **`dataset`** ties a recipe to one [data set](/docs/concepts#data-set), which keeps the recipes of one data set apart from another's.
- **`integration`** records which [integration](/docs/concepts#integration) imported the recipe, so that records can be traced back to their source. It is optional, since a record can also be created by hand. With `on_delete=models.CASCADE`, deleting an integration also deletes the recipes it imported.
- **`external_id` and the unique constraint** identify a recipe in the system it came from. The sync on the [next page](/docs/customization/tutorial/integrations) uses the pair `(dataset, external_id)` to update a recipe that it has seen before instead of creating a second copy.
- **`allergens` and `dietary_tags`** are lists computed when a recipe is imported. They let the retriever and the validator exclude recipes without asking a language model whether a dish is safe.
- **`calories`** is per serving. The meal plan multiplies it by the number of servings.
- **`EntityMeta`** is everything Suvereo needs to show the entity in the UI: a URL slug, the plural label of the sidebar entry and the columns of the table. No serializer, view or frontend code is needed.
- **`get_indexable_content()`** returns the text that is embedded. Search finds recipes by the similarity of a query to this text, so it contains what a person would search by: the title, the kind of meal, the ingredients, the dietary tags and the instructions. The allergens are left out, because the retriever filters on them exactly.

## 3. Making the recipe searchable

A chunk stores one piece of an entity's indexable text together with its embedding. Add one to the recipe:

```python
# diet_domain/models/recipe_chunk.py
from django.db import models
from suvereo_common.indexing import BaseEmbeddingChunk


class RecipeChunk(BaseEmbeddingChunk):
    recipe = models.ForeignKey("diet_domain.Recipe", on_delete=models.CASCADE, related_name="chunks")
```

`BaseEmbeddingChunk` provides the `content` and `embedding` fields. The relation must be named `chunks` on the entity's side, since the indexer that Suvereo provides looks for it. The indexer splits the text from `get_indexable_content()` into pieces, embeds them with the embedding model of the recipe's data set and replaces the stored chunks of the recipe. The domain definition calls it once per synced recipe, as shown on the next page.

## 4. The user profile entity

The profile holds what the agent must know about a person. It is an entity so that the profiles are stored, listed in the UI and available to the execution, but agents do not search it by meaning, so it has no chunk model and no `get_indexable_content()`:

```python
# diet_domain/models/user_profile.py
from django.conf import settings
from django.db import models
from suvereo_common.entities import DomainEntity, EntityField


class UserProfile(DomainEntity, models.Model):
    dataset = models.ForeignKey("catalog.DataSet", on_delete=models.CASCADE, related_name="user_profiles")
    integration = models.ForeignKey(
        "catalog.Integration", on_delete=models.CASCADE, related_name="user_profiles", null=True, blank=True
    )
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="diet_profile")
    allergies = models.JSONField(default=list, blank=True)
    conditions = models.JSONField(default=list, blank=True)
    dietary_preferences = models.JSONField(default=list, blank=True)
    disliked_foods = models.JSONField(default=list, blank=True)
    target_calories = models.PositiveIntegerField(null=True, blank=True)

    class EntityMeta:
        slug = "user-profiles"
        label = "User profiles"
        list_fields = [
            EntityField("user_email", label="User"),
            EntityField("allergies"),
            EntityField("conditions"),
            EntityField("dietary_preferences", label="Preferences"),
            EntityField("target_calories", label="Calories target"),
        ]

    @property
    def user_email(self) -> str:
        return self.user.email

    def __str__(self) -> str:
        return f"Diet profile of {self.user_email}"
```

Two things differ from the recipe:

- **The profile points at a Suvereo user.** A domain definition can reference the user model through `settings.AUTH_USER_MODEL`, so the profile of a person is found from the account they sign in with. `OneToOneField` makes it one profile per user.
- **A list field can name a read-only property.** `user_email` is not a column. Suvereo builds the table's serializer from the field names, so a property is listed like a column.

Re-export the models, so that they can be imported from `diet_domain.models` and found by Django:

```python
# diet_domain/models/__init__.py
from .recipe import Recipe
from .recipe_chunk import RecipeChunk
from .user_profile import UserProfile

__all__ = ["Recipe", "RecipeChunk", "UserProfile"]
```

## 5. The recipe retriever

A [retriever](/docs/customization/domain-definitions#2-retrievers) is the object a tool calls to search an entity. `BaseVectorStoreRetriever` embeds a query and returns the closest chunks within one data set. The diet domain definition adds the filters that matter for food:

```python
# diet_domain/retrievers/recipe.py
from typing import Optional

from suvereo_common.retrievers import BaseVectorStoreRetriever

from diet_domain.models import Recipe, RecipeChunk
from diet_domain.structures import Allergen, MealType

MAX_RECIPES_RETURNED = 20


class RecipeRetriever(BaseVectorStoreRetriever[RecipeChunk]):
    chunk_model = RecipeChunk
    dataset_filter = "recipe__dataset_id"

    def find_recipes(
        self, query: str, excluded_allergens: list[Allergen] | None = None, meal_type: Optional[MealType] = None
    ) -> list[Recipe]:
        excluded = set(excluded_allergens or [])
        recipes: dict[int, Recipe] = {}
        for chunk in self.find_content_matching_query(query):
            recipe = chunk.recipe
            if meal_type and recipe.meal_type != meal_type:
                continue
            if excluded.intersection(recipe.allergens):
                continue
            recipes.setdefault(recipe.id, recipe)
        return list(recipes.values())[:MAX_RECIPES_RETURNED]
```

```python
# diet_domain/retrievers/__init__.py
from .recipe import RecipeRetriever

__all__ = ["RecipeRetriever"]
```

- `chunk_model` is the table to search, and `dataset_filter` is the path from a chunk to its data set id. Together they keep a search inside the data set of the conversation.
- `find_content_matching_query(query)` is the vector search that the base class provides. `find_recipes` narrows its result: it drops recipes of another kind of meal and recipes that contain an excluded allergen, and it collapses several chunks of one recipe into one result.
- The filters run after the vector search, on the chunks that it returned, so a query that matches mostly excluded recipes returns fewer results. How many chunks the search returns is set when the builder creates the retriever, in the next step.

## 6. The profile accessor, the injector and the builder

Tools reach the domain definition's code through the [injector](/docs/agents/injector), and the [builder](/docs/agents/builder) creates the injector. The injector holds two things here: the retriever, and an accessor for the profile of the user in the conversation.

The accessor is bound to one user when it is created. It reads and updates that user's profile and nothing else, so a tool that uses it cannot reach another person's data, whatever the model asks for:

```python
# diet_domain/profiles.py
from typing import Any, Optional

from diet_domain.models import UserProfile

UPDATABLE_FIELDS = (
    "allergies",
    "conditions",
    "dietary_preferences",
    "disliked_foods",
    "target_calories",
)


class UserProfileAccessor:
    def __init__(self, user_id: int, data_set_id: int):
        self._user_id = user_id
        self._data_set_id = data_set_id

    def get(self) -> Optional[UserProfile]:
        return UserProfile.objects.filter(user_id=self._user_id).first()

    def update(self, changes: dict[str, Any]) -> UserProfile:
        accepted = {field: value for field, value in changes.items() if field in UPDATABLE_FIELDS}
        profile, _ = UserProfile.objects.update_or_create(
            user_id=self._user_id,
            defaults=accepted,
            create_defaults={"dataset_id": self._data_set_id, **accepted},
        )
        return profile
```

`UPDATABLE_FIELDS` lists the fields that can be changed through the accessor. Anything else in `changes` is ignored. The first update creates the profile, in the data set of the conversation.

The injector extends the default one:

```python
# diet_domain/injector.py
from suvereo_common.injectors import Injector

from diet_domain.profiles import UserProfileAccessor
from diet_domain.retrievers import RecipeRetriever


class DietInjector(Injector):
    def __init__(self, *args, recipe_retriever: RecipeRetriever, user_profile: UserProfileAccessor, **kwargs):
        super().__init__(*args, **kwargs)
        self._recipe_retriever = recipe_retriever
        self._user_profile = user_profile

    @property
    def recipe_retriever(self) -> RecipeRetriever:
        return self._recipe_retriever

    @property
    def user_profile(self) -> UserProfileAccessor:
        return self._user_profile
```

The builder creates it. The builder of the domain definition subclasses `AgentBuilder` and overrides `_build_injector()`:

```python
# diet_domain/builder.py
from suvereo_common.builder import AgentBuilder
from suvereo_common.config import AgentConfig

from diet_domain.injector import DietInjector
from diet_domain.profiles import UserProfileAccessor
from diet_domain.retrievers import RecipeRetriever

CHUNKS_SEARCHED = 100


class DietAgentBuilder(AgentBuilder[AgentConfig]):
    def _build_injector(self) -> DietInjector:
        chat_history = self._build_chat_history()
        memory_compactor = self._build_memory_compactor(chat_history)
        return DietInjector(
            recipe_retriever=self._build_recipe_retriever(),
            user_profile=self._build_user_profile_accessor(),
            repositories=self._repositories,
            chat_history=chat_history,
            memory_compactor=memory_compactor,
            tool_scratchpad=self._tool_scratchpad,
        )

    def _build_recipe_retriever(self) -> RecipeRetriever:
        return RecipeRetriever(
            data_set_id=self._data_set_id,
            embeddings_registry=self._embeddings_registry,
            searcher=self._config.similarity_searcher(),
            max_objects=CHUNKS_SEARCHED,
        )

    def _build_user_profile_accessor(self) -> UserProfileAccessor:
        conversation = self._repositories.conversation.get_by_id(self.conversation_id)
        return UserProfileAccessor(user_id=conversation.user_id, data_set_id=self._data_set_id)
```

By the time `_build_injector()` runs, the base builder has resolved the data set of the conversation and created the embedding registry, so the builder only assembles what is specific to the domain. `_build_recipe_retriever()` passes:

- `data_set_id` and `embeddings_registry` let the retriever embed the query with the embedding model of the data set.
- `searcher` is the similarity searcher of the agent's configuration. Its default is the one the framework provides, which compares embeddings in the database.
- `max_objects` is the number of chunks the search returns before the retriever filters them. A larger number gives the filters more to work with.
- `_build_user_profile_accessor()` finds the user of the conversation, `conversation.user_id`, and binds the accessor to them. The conversation is identified by `self.conversation_id`, which the builder is created with.
- The remaining arguments are what the default injector needs, and are passed on unchanged.

The builder takes effect when an agent names it. The [agent page](/docs/customization/tutorial/agent) sets it with `BUILDER_CLASS`.

## 7. Register the domain definition

Registration tells Suvereo that the domain definition exists. Edit `server/pecl/settings_override.py`. In a codebase that has no other domain definition, the file needs only these entries:

```python
INSTALLED_DOMAIN_DEFINITIONS = ["diet_domain"]

CATALOG_ENTITY_PLUGINS = [
    "diet_domain.models.Recipe",
    "diet_domain.models.UserProfile",
]
```

| Setting | Effect |
|---|---|
| `INSTALLED_DOMAIN_DEFINITIONS` | Adds the app to Django's `INSTALLED_APPS`, so its models and migrations are found. |
| `CATALOG_ENTITY_PLUGINS` | Lists the entities that appear in the UI. The chunk model is not listed, since it is not shown to users. |

## 8. Create the tables

Generate the migrations from the `server/` directory and apply them:

```bash
./manage.py makemigrations diet_domain
./manage.py migrate
```

`makemigrations` writes `0001_initial.py` into `diet_domain/migrations/`, because the package is installed in editable mode. It reports the three models and the unique constraint:

```
Migrations for 'diet_domain':
  diet_domain/migrations/0001_initial.py
    + Create model Recipe
    + Create model RecipeChunk
    + Create model UserProfile
    + Create constraint uq_diet_recipe on model recipe
```

Commit the migration with the package. The migration declares a dependency on the `catalog` app, which holds data sets and integrations, so it is applied after that app's tables exist.

## Check the result

Restart the server and the worker, so that they read the new settings. Open a data set in the UI. Its sidebar now has a **Catalog** section with two entries, **Recipes** and **User profiles**, each listing an empty table with the columns declared in `EntityMeta`.

Nothing fills the tables yet. The [next page](/docs/customization/tutorial/integrations) adds the integrations that do.
