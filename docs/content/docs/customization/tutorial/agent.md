# The Agent

The vertical now holds recipes and profiles. This page adds an [agent](/docs/concepts#agent) that uses them: a nutrition assistant that a user can talk to, and that suggests meals through a [tool](/docs/concepts#tool) which searches the recipes. The parts of an agent are described in [Agent architecture](/docs/agents/agent-architecture), and the class that this page uses in [Agent classes](/docs/agents/agent-classes).

An agent can live in its own plugin, in a vertical or in the Suvereo codebase. This tutorial puts it in the vertical, in a sub-package, so that the vertical's builder and the agent that needs it stay together.

New files on this page:

```
diet_vertical/
└── nutrition_agent/
    ├── __init__.py
    ├── agent.py
    ├── prompt.py
    └── tools/
        ├── __init__.py
        └── search_recipes_tool.py
```

## 1. The tool

A tool is what the language model calls to get something done. Two things decide how well it is used: the description the model reads, and what the tool returns. This one gives the model the recipe search, including the filters that matter for a diet:

```python
# diet_vertical/nutrition_agent/tools/search_recipes_tool.py
import json
from typing import Optional

from pydantic import BaseModel, Field
from suvereo_common.tools import BaseLLMTool

from diet_vertical.models import Recipe
from diet_vertical.structures import Allergen, MealType


def recipe_as_dict(recipe: Recipe) -> dict:
    return {
        "recipe_id": recipe.id,
        "title": recipe.title,
        "meal_type": recipe.meal_type,
        "ingredients": recipe.ingredients,
        "allergens": recipe.allergens,
        "dietary_tags": recipe.dietary_tags,
        "calories_per_serving": recipe.calories,
    }


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

```python
# diet_vertical/nutrition_agent/tools/__init__.py
from .search_recipes_tool import SearchRecipesTool

__all__ = ["SearchRecipesTool"]
```

- **`ARGS_SCHEMA`** is the input the model fills in. Suvereo derives the tool's definition for the model from it, and the `description` of each field is part of that definition. Typing `excluded_allergens` as a list of `Allergen` and `meal_type` as `MealType` puts the allowed values in the schema, so the model is told which ones exist and the input is validated against them. The values are the same ones the recipes store.
- **`DESCRIPTION`** tells the model when to use the tool. The last sentence asks it to pass the allergies, which is the instruction that keeps unsafe recipes out of the answer. The prompt repeats it.
- **`run()`** is where the vertical is used. The tool reaches the retriever through `self._injector`, which is the `DietInjector` created by the vertical's builder, and returns JSON for the model to read. The recipe is serialized with its `recipe_id`, so that a later step can refer to it exactly. A message instead of an empty list tells the model to retry with a broader query.
- **`RETURN_DIRECT = False`** sends the result back to the model, which writes the answer. See [Tools](/docs/agents/tools) for the other base classes and for tools that return their result to the user as it is.

## 2. The prompt

The system prompt sets the role and the rules of the assistant:

```python
# diet_vertical/nutrition_agent/prompt.py
NUTRITION_ASSISTANT_PROMPT = """
You are a nutrition assistant. You suggest meals that suit the user you are talking to.

- Ask about the user's allergies, dietary preferences and disliked foods if you do not know them.
- Find recipes with search_recipes. Pass the user's allergies as excluded_allergens, and meal_type when they ask for
  a particular meal.
- Never suggest a recipe containing something the user is allergic to.
- Mention the calories per serving of each recipe you suggest.
- You are not a doctor: for medical questions, recommend consulting one.
"""
```

The prompt names the tool, so the model knows what to call. The assistant in this tutorial cannot read the user's profile, since it has no tool for it, and so the first rule makes it ask. A prompt can also contain `{variable}` placeholders that are filled from settings entered in the UI, see [Prompts](/docs/agents/prompts).

## 3. The agent class

An agent declares its own configuration as class variables. `BaseToolCallingAgent`, from `suvereo-agent-tool-calling`, runs the loop in which the model calls tools until it can answer, and the class only says what is specific to the assistant:

```python
# diet_vertical/nutrition_agent/agent.py
from suvereo_agent_tool_calling import BaseToolCallingAgent
from suvereo_common.config import LLMToolConfig

from diet_vertical.builder import DietAgentBuilder

from .prompt import NUTRITION_ASSISTANT_PROMPT
from .tools import SearchRecipesTool


class NutritionAssistantAgent(BaseToolCallingAgent):
    AGENT_KEY = "nutrition-assistant"
    NAME = "Nutrition assistant"
    SYSTEM_PROMPT = NUTRITION_ASSISTANT_PROMPT
    BUILDER_CLASS = DietAgentBuilder
    TOOLS = [LLMToolConfig(tool_class=SearchRecipesTool)]
```

```python
# diet_vertical/nutrition_agent/__init__.py
from .agent import NutritionAssistantAgent

__all__ = ["NutritionAssistantAgent"]
```

| Variable | What it does here |
|---|---|
| `AGENT_KEY` | The identifier of the agent class. The execution on the [next page](/docs/customization/tutorial/agentic-execution) refers to it. |
| `NAME` | The name shown in the list of agent types in the UI. |
| `SYSTEM_PROMPT` | The prompt of step 2. |
| `BUILDER_CLASS` | The builder from the [vertical page](/docs/customization/tutorial/vertical#6-the-injector-and-the-builder). This is the line that connects the agent to the vertical: without it, the agent is built with the default builder, and its tool would not find `recipe_retriever` on the injector. |
| `TOOLS` | The tools of the agent. `LLMToolConfig` wraps a tool class together with its settings. |

An agent declares more than this, such as the settings an admin can change in the UI and the size of the conversation history that is sent to the model. They have defaults, and the page [Agent classes](/docs/agents/agent-classes) lists them.

## 4. Register the agent

Add the class to `server/pecl/settings_override.py`:

```python
AVAILABLE_AGENTS = [
    "diet_vertical.nutrition_agent.NutritionAssistantAgent",
]
```

Restart the server and the worker.

## Try it

1. Open your data set. Under **Configure** go to **Agents** and choose **New agent**.
2. Select the type **Nutrition assistant**, give the agent a name and save it.
3. Under **Ask**, choose the new agent and start a conversation. An admin can use the agent, and so can a user who has the **Agent Interaction** role. The users from the sample source have it, with the password `test123`.
4. Write a request that depends on the data, such as: *"I'm allergic to peanuts. Suggest a dinner."*

The agent is expected to call `search_recipes` with `peanuts` in `excluded_allergens` and `main` as the meal type. Its answer lists recipes from the data set, with their calories, and leaves out "Peanut noodles", which the retriever filters out. The wording of the answer varies with the language model.

If the agent answers without recipes, check that the recipe sync has finished and that the data set has an embedding model: the search finds recipes through their embeddings.

Continue with [the agentic execution](/docs/customization/tutorial/agentic-execution).
