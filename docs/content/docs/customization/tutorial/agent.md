# The Agent

The domain definition now holds recipes and profiles. This page adds an [agent](/docs/concepts#agent) that uses them: a nutrition assistant that a user can talk to, and that suggests meals through [tools](/docs/concepts#tool) which search the recipes and read and update the user's profile. The parts of an agent are described in [Agent architecture](/docs/agents/agent-architecture), and the class that this page uses in [Agent classes](/docs/agents/agent-classes).

An agent can live in its own plugin, in a domain definition or in the Suvereo codebase. This tutorial puts it in the domain definition, in a sub-package, so that the domain definition's builder and the agent that needs it stay together.

New files on this page:

```
diet_domain/
└── nutrition_agent/
    ├── __init__.py
    ├── agent.py
    ├── prompt.py
    └── tools/
        ├── __init__.py
        ├── serialization.py
        ├── search_recipes_tool.py
        ├── get_user_profile_tool.py
        └── update_user_profile_tool.py
```

## 1. The recipe search tool

A tool is what the language model calls to get something done. Two things decide how well it is used: the description the model reads, and what the tool returns. The first tool gives the model the recipe search, including the filters that matter for a diet. The tools share a small file that turns recipes and profiles into dictionaries for the model:

```python
# diet_domain/nutrition_agent/tools/serialization.py
from typing import Any

from diet_domain.models import Recipe, UserProfile
from diet_domain.profiles import UPDATABLE_FIELDS


def recipe_as_dict(recipe: Recipe) -> dict[str, Any]:
    return {
        "recipe_id": recipe.id,
        "title": recipe.title,
        "meal_type": recipe.meal_type,
        "ingredients": recipe.ingredients,
        "allergens": recipe.allergens,
        "dietary_tags": recipe.dietary_tags,
        "calories_per_serving": recipe.calories,
    }


def profile_as_dict(profile: UserProfile) -> dict[str, Any]:
    return {field: getattr(profile, field) for field in UPDATABLE_FIELDS}
```

```python
# diet_domain/nutrition_agent/tools/search_recipes_tool.py
import json
from typing import Optional

from pydantic import BaseModel, Field
from suvereo_common.tools import BaseLLMTool

from diet_domain.nutrition_agent.tools.serialization import recipe_as_dict
from diet_domain.structures import Allergen, MealType


class SearchRecipesInput(BaseModel):
    query: str = Field(description="What the recipe should be like, e.g. 'high protein vegetarian dinner'.")
    excluded_allergens: list[Allergen] = Field(
        default_factory=list, description="Allergens the recipes must not contain."
    )
    meal_type: Optional[MealType] = Field(
        default=None,
        description="Limits the results to one kind of meal: breakfast, main (for lunch or dinner) or snack.",
    )


class SearchRecipesTool(BaseLLMTool):
    NAME = "search_recipes"
    DESCRIPTION = (
        "Finds recipes similar to the query, with ingredients, allergens and nutrition per serving. "
        "Always pass the user's allergies as excluded_allergens."
    )
    ARGS_SCHEMA = SearchRecipesInput
    RETURN_DIRECT = False

    def run(
        self, query: str, excluded_allergens: list[Allergen] | None = None, meal_type: Optional[MealType] = None
    ) -> str:
        recipes = self._injector.recipe_retriever.find_recipes(query, excluded_allergens, meal_type)
        if not recipes:
            return "No matching recipes found, try a broader query."
        return json.dumps([recipe_as_dict(recipe) for recipe in recipes])
```

- **`ARGS_SCHEMA`** is the input the model fills in. Suvereo derives the tool's definition for the model from it, and the `description` of each field is part of that definition. Typing `excluded_allergens` as a list of `Allergen` and `meal_type` as `MealType` puts the allowed values in the schema, so the model is told which ones exist and the input is validated against them. The values are the same ones the recipes store.
- **`DESCRIPTION`** tells the model when to use the tool. The last sentence asks it to pass the allergies, which is the instruction that keeps unsafe recipes out of the answer. The prompt repeats it.
- **`run()`** is where the domain definition is used. The tool reaches the retriever through `self._injector`, which is the `DietInjector` created by the domain definition's builder, and returns JSON for the model to read. The recipe is serialized with its `recipe_id`, so that a later step can refer to it exactly. A message instead of an empty list tells the model to retry with a broader query.
- **`RETURN_DIRECT = False`** sends the result back to the model, which writes the answer. See [Tools](/docs/agents/tools) for the other base classes and for tools that return their result to the user as it is.

## 2. The profile tools

The assistant should know who it is talking to, and remember what they say. Two tools read and change the user's profile:

```python
# diet_domain/nutrition_agent/tools/get_user_profile_tool.py
import json

from pydantic import BaseModel
from suvereo_common.tools import BaseLLMTool

from diet_domain.nutrition_agent.tools.serialization import profile_as_dict


class GetUserProfileInput(BaseModel):
    pass


class GetUserProfileTool(BaseLLMTool):
    NAME = "get_user_profile"
    DESCRIPTION = (
        "Returns the health profile of the user you are talking to: allergies, conditions, preferences, "
        "body parameters and daily targets. Call it before suggesting meals."
    )
    ARGS_SCHEMA = GetUserProfileInput
    RETURN_DIRECT = False

    def run(self) -> str:
        profile = self._injector.user_profile.get()
        if profile is None:
            return "The user has no profile yet. Ask about their allergies, preferences and goals and save them."
        return json.dumps(profile_as_dict(profile))
```

```python
# diet_domain/nutrition_agent/tools/update_user_profile_tool.py
import json
from typing import Optional

from pydantic import BaseModel, Field
from suvereo_common.tools import BaseLLMTool

from diet_domain.nutrition_agent.tools.serialization import profile_as_dict
from diet_domain.structures import Allergen


class UpdateUserProfileInput(BaseModel):
    allergies: Optional[list[Allergen]] = Field(
        default=None,
        description="Complete list of allergies, replacing the current one.",
    )
    conditions: Optional[list[str]] = Field(
        default=None, description="Complete list of health conditions, replacing the current one."
    )
    dietary_preferences: Optional[list[str]] = Field(
        default=None, description="Complete list of dietary preferences (e.g. vegan), replacing the current one."
    )
    disliked_foods: Optional[list[str]] = Field(
        default=None, description="Complete list of disliked foods, replacing the current one."
    )
    target_calories: Optional[int] = Field(default=None, description="Daily calorie target.")


class UpdateUserProfileTool(BaseLLMTool):
    NAME = "update_user_profile"
    DESCRIPTION = (
        "Saves changes to the user's profile when they mention something new (an allergy, a diagnosis, a new calorie "
        "target). Send only the fields that change. List fields replace the stored list, so read the profile first "
        "and send the complete list."
    )
    ARGS_SCHEMA = UpdateUserProfileInput
    RETURN_DIRECT = False

    def run(self, **changes) -> str:
        changes = {field: value for field, value in changes.items() if value is not None}
        if not changes:
            return "Nothing to update."
        profile = self._injector.user_profile.update(changes)
        return json.dumps(profile_as_dict(profile))
```

```python
# diet_domain/nutrition_agent/tools/__init__.py
from .get_user_profile_tool import GetUserProfileTool
from .search_recipes_tool import SearchRecipesTool
from .update_user_profile_tool import UpdateUserProfileTool

__all__ = ["GetUserProfileTool", "SearchRecipesTool", "UpdateUserProfileTool"]
```

- **`get_user_profile` takes no arguments.** The model does not say whose profile it wants, so it cannot ask for another person's.
- **`update_user_profile` has optional fields.** The model sends only what changed. A list replaces the stored one, so the description tells the model to read the profile first and send the complete list. The tool drops the fields that were not sent before it calls the accessor.
- **Both go through `self._injector.user_profile`**, the accessor from the [domain definition page](/docs/customization/tutorial/domain-definition#6-the-profile-accessor-the-injector-and-the-builder), which the builder bound to the user of the conversation.

### What a tool can reach

A tool acts with the authority of whoever is in the conversation, and it should reach no more than that:

- **The scope is set in code, not by the model.** The tools have no `user_id` argument. If they had, the model could pass any id, including one it was talked into by a message such as "update the profile of user 1". The accessor takes the user from the conversation, which the model cannot change, and the tool schema does not offer a way to choose.
- **The accessor limits what a tool can do.** It exposes reading and updating of the profile, only of the listed fields. A tool cannot delete a profile or change the link to the user.
- **The data set is fixed too.** A profile created through the tool belongs to the data set of the conversation.

The model decides when to call a tool and with which values, so what it passes is input to validate, as that of any other client. The schema validates the types, and the accessor narrows the fields. A tool that can do more, such as one that acts on other users, needs its own check of who is allowed to do it.

## 3. The prompt

The system prompt sets the role and the rules of the assistant:

```python
# diet_domain/nutrition_agent/prompt.py
NUTRITION_ASSISTANT_PROMPT = """
You are a nutrition assistant. You suggest meals that suit the user you are talking to.

- Start with get_user_profile. Ask about the allergies, conditions, dietary preferences and disliked foods that are
  missing from it.
- When the user tells you something new about themselves, save it with update_user_profile.
- Find recipes with search_recipes. Pass the user's allergies as excluded_allergens, and meal_type when they ask for
  a particular meal.
- Never suggest a recipe containing something the user is allergic to.
- Mention the calories per serving of each recipe you suggest.
- You are not a doctor: for medical questions, recommend consulting one.
"""
```

The prompt names the tools, so the model knows what to call. The first rule makes the assistant read the profile before suggesting anything, and the second makes it save what the user says. A prompt can also contain `{variable}` placeholders that are filled from settings entered in the UI, see [Prompts](/docs/agents/prompts).

## 4. The agent class

An agent declares its own configuration as class variables. `BaseToolCallingAgent`, from `suvereo-agent-tool-calling`, runs the loop in which the model calls tools until it can answer, and the class only says what is specific to the assistant:

```python
# diet_domain/nutrition_agent/agent.py
from suvereo_agent_tool_calling import BaseToolCallingAgent
from suvereo_common.config import LLMToolConfig

from diet_domain.builder import DietAgentBuilder

from .prompt import NUTRITION_ASSISTANT_PROMPT
from .tools import GetUserProfileTool, SearchRecipesTool, UpdateUserProfileTool


class NutritionAssistantAgent(BaseToolCallingAgent):
    AGENT_KEY = "nutrition-assistant"
    NAME = "Nutrition assistant"
    SYSTEM_PROMPT = NUTRITION_ASSISTANT_PROMPT
    BUILDER_CLASS = DietAgentBuilder
    TOOLS = [
        LLMToolConfig(tool_class=GetUserProfileTool),
        LLMToolConfig(tool_class=SearchRecipesTool),
        LLMToolConfig(tool_class=UpdateUserProfileTool),
    ]
```

```python
# diet_domain/nutrition_agent/__init__.py
from .agent import NutritionAssistantAgent

__all__ = ["NutritionAssistantAgent"]
```

| Variable | What it does here |
|---|---|
| `AGENT_KEY` | The identifier of the agent class. The execution on the [next page](/docs/customization/tutorial/agentic-execution) refers to it. |
| `NAME` | The name shown in the list of agent types in the UI. |
| `SYSTEM_PROMPT` | The prompt of step 3. |
| `BUILDER_CLASS` | The builder from the [domain definition page](/docs/customization/tutorial/domain-definition#6-the-profile-accessor-the-injector-and-the-builder). This is the line that connects the agent to the domain definition: without it, the agent is built with the default builder, and its tools would not find `recipe_retriever` or `user_profile` on the injector. |
| `TOOLS` | The tools of the agent. `LLMToolConfig` wraps a tool class together with its settings. |

An agent declares more than this, such as the settings an admin can change in the UI and the size of the conversation history that is sent to the model. They have defaults, and the page [Agent classes](/docs/agents/agent-classes) lists them.

## 5. Register the agent

Add the class to `server/pecl/settings_override.py`:

```python
AVAILABLE_AGENTS = [
    "diet_domain.nutrition_agent.NutritionAssistantAgent",
]
```

Restart the server and the worker.

## Try it

1. Open your data set. Under **Configure** go to **Agents** and choose **New agent**.
2. Select the type **Nutrition assistant**, give the agent a name and save it.
3. Under **Ask**, choose the new agent and start a conversation. An admin can use the agent, and so can a user who has the **Agent Interaction** role. The users from the sample source have it, with the password `test123`.
4. Write a request that depends on the data, such as: *"I'm allergic to peanuts. Suggest a dinner."*

The agent is expected to call `get_user_profile` first. If the profile has no allergies, it asks, and when you answer it saves them with `update_user_profile`. Then it calls `search_recipes` with `peanuts` in `excluded_allergens` and `main` as the meal type. Its answer lists recipes from the data set, with their calories, and leaves out "Peanut noodles", which the retriever filters out. The wording of the answer varies with the language model.

To see the limit of the tools, open **User profiles** in the catalog while a conversation is running. A profile that the agent saves appears there for the user you are logged in as, and for no one else, whatever you ask for in the conversation.

If the agent answers without recipes, check that the recipe sync has finished and that the data set has an embedding model: the search finds recipes through their embeddings.

Continue with [the agentic execution](/docs/customization/tutorial/agentic-execution).
