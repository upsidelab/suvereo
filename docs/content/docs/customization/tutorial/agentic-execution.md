# The Agentic Execution

A conversation answers one person as they type. The last part of the tutorial adds the other mode of working: an [agentic execution](/docs/concepts#agentic-execution), which runs in the background, takes structured input and returns a structured result, with no one to answer questions on the way. The execution built here creates a meal plan for a user for a number of days, and checks the plan against the user's allergies and calorie target before it is accepted.

The classes an execution is made of are described in [Agentic execution](/docs/agents/agentic-execution). This page builds one for the nutrition assistant from the [previous page](/docs/customization/tutorial/agent). It runs on the same agent, with its own prompt and a smaller set of tools.

New files on this page:

```
diet_domain/
└── nutrition_agent/
    ├── __init__.py              # extended
    ├── prompt.py                # extended
    ├── validators/              # a package, see step 3
    └── execution_definition.py
```

## 1. The input

The input is a Pydantic model. The server derives the JSON Schema of the API from it and rejects a request that does not match it:

```python
# diet_domain/nutrition_agent/execution_definition.py (the top of the file, shown in full in step 4)
from pydantic import Field
from suvereo_common.agentic_execution import ExecutionInputType


class WeeklyMealPlanInput(ExecutionInputType):
    user_id: int = Field(description="Id of the user the plan is made for.")
    days: int = Field(default=7, ge=1, le=14, description="Number of days to plan.")
```

The plan is for a user other than the caller. The caller is whoever authenticates the API request, such as a service account that runs the plan for each user once a week.

## 2. The prompt

An execution can replace the agent's conversation prompt with one of its own. The assistant's conversation prompt assumes a person to talk to, and an execution has none, so add a second prompt to `prompt.py`:

```python
WEEKLY_MEAL_PLAN_EXECUTION_PROMPT = """
You build meal plans in an autonomous execution: no human can answer your questions.
You are given a user's profile and a number of days to plan.

- Plan breakfast, lunch and dinner for every day, and snacks if they help reach the calorie target.
- Find recipes with search_recipes. Pass the user's allergies as excluded_allergens, and the meal_type: breakfast,
  main (for lunch and dinner) or snack. Use only recipe_id values it returns.
- Respect the user's conditions, dietary preferences and disliked foods.
- Choose servings so that each day's calories are within 10% of the user's calorie target. If there is no target,
  plan an ordinary day of eating.
- A recipe may repeat, but keep repeats rare and spread them across the days.

Respond with JSON only, in this shape:
{{"days": [{{"day": 1, "meals": [{{"meal": "breakfast", "recipe_id": 12, "servings": 1.0}}]}}]}}

Call stop_execution with a short reason only if search_recipes finds no safe recipe for a meal.
"""
```

- The prompt states the output format exactly, because the validators in the next step parse it.
- The braces of the JSON example are doubled, since prompts are formatted with `str.format`.
- `stop_execution` is a tool that ends the execution as failed with a reason. It gives the agent a way out when no plan is possible, instead of returning an invented one. The definition lists it among its tools in step 4.

## 3. The validators

A model's answer can be well formed and still wrong. A validator checks the answer in code. When it rejects the answer, it returns feedback, which is sent to the model so it can correct the plan, and the execution tries again, up to `MAX_RETRIES` times (3 by default). Validators run in order and the first one that fails decides what happens, so each is small and checks one thing. The earlier ones guarantee what the later ones can assume.

Each validator is a small file in a `validators` package. The files of this step:

```
diet_domain/nutrition_agent/validators/
├── __init__.py
├── shared.py
├── meal_plan_json.py
├── all_days_planned.py
├── recipes_exist.py
├── no_allergens.py
└── calorie_target.py
```

The plan is described once, as Pydantic models, in `shared.py`. The small helpers next to them share the parsing and the database lookups:

```python
# diet_domain/nutrition_agent/validators/shared.py
from typing import Literal

from pydantic import BaseModel, Field
from suvereo_common.agentic_execution import (
    ExecutionInputType,
    ValidatorFailureResponse,
    ValidatorResponse,
    ValidatorSuccessResponse,
)

from diet_domain.models import Recipe, UserProfile


class PlannedMeal(BaseModel):
    meal: Literal["breakfast", "lunch", "dinner", "snack"]
    recipe_id: int
    servings: float = Field(gt=0)


class PlannedDay(BaseModel):
    day: int
    meals: list[PlannedMeal] = Field(min_length=1)


class MealPlan(BaseModel):
    days: list[PlannedDay]


def parse_plan(response: str) -> MealPlan:
    return MealPlan.model_validate_json(response)


def load_recipes(plan: MealPlan) -> dict[int, Recipe]:
    return Recipe.objects.in_bulk({meal.recipe_id for day in plan.days for meal in day.meals})


def get_profile(execution_input: ExecutionInputType) -> UserProfile | None:
    return UserProfile.objects.filter(user_id=execution_input.user_id).first()


def reject(problems: list[str]) -> ValidatorResponse:
    if problems:
        return ValidatorFailureResponse(feedback="The plan was rejected:\n- " + "\n- ".join(problems))
    return ValidatorSuccessResponse()
```

The validators follow, one per file. First the check that the later ones rely on:

```python
# diet_domain/nutrition_agent/validators/meal_plan_json.py
from pydantic import ValidationError
from suvereo_common.agentic_execution import (
    ExecutionInputType,
    IsValidJsonValidator,
    ToolScratchpad,
    ValidatorFailureResponse,
    ValidatorResponse,
    ValidatorSuccessResponse,
)

from .shared import parse_plan


class MealPlanJsonValidator(IsValidJsonValidator):
    """Overrides the JSON check: the response must be JSON that has the shape of a meal plan."""

    def validate(
        self, response: str, execution_input: ExecutionInputType, tool_scratchpad: ToolScratchpad
    ) -> ValidatorResponse:
        failure = super().validate(response, execution_input, tool_scratchpad)
        if not failure.validation_successful:
            return failure
        try:
            parse_plan(response)
        except ValidationError as error:
            problems = [f"{'.'.join(map(str, e['loc']))}: {e['msg']}" for e in error.errors()]
            return ValidatorFailureResponse(
                feedback='The JSON does not have the shape of a meal plan, {"days": [{"day": 1, "meals": '
                '[{"meal": "lunch", "recipe_id": 1, "servings": 1.0}]}]}:\n- ' + "\n- ".join(problems)
            )
        return ValidatorSuccessResponse()
```

Then the checks of the plan's content:

```python
# diet_domain/nutrition_agent/validators/all_days_planned.py
from suvereo_common.agentic_execution import (
    BaseExecutionValidator,
    ExecutionInputType,
    ToolScratchpad,
    ValidatorResponse,
    ValidatorSuccessResponse,
)

from .shared import parse_plan, reject


class AllDaysPlannedValidator(BaseExecutionValidator):
    """Checks that the plan covers each requested day exactly once."""

    def validate(
        self, response: str, execution_input: ExecutionInputType, tool_scratchpad: ToolScratchpad
    ) -> ValidatorResponse:
        days = sorted(day.day for day in parse_plan(response).days)
        expected = list(range(1, execution_input.days + 1))
        if days != expected:
            return reject([f"The plan must contain each of the days 1 to {execution_input.days} once, got {days}."])
        return ValidatorSuccessResponse()
```

```python
# diet_domain/nutrition_agent/validators/recipes_exist.py
from suvereo_common.agentic_execution import (
    BaseExecutionValidator,
    ExecutionInputType,
    ToolScratchpad,
    ValidatorResponse,
)

from .shared import load_recipes, parse_plan, reject


class RecipesExistValidator(BaseExecutionValidator):
    """Checks that every recipe_id is one that exists, so the model cannot invent recipes."""

    def validate(
        self, response: str, execution_input: ExecutionInputType, tool_scratchpad: ToolScratchpad
    ) -> ValidatorResponse:
        plan = parse_plan(response)
        recipes = load_recipes(plan)
        return reject(
            [
                f"Day {day.day}: recipe_id {meal.recipe_id} does not exist, use ids from search_recipes."
                for day in plan.days
                for meal in day.meals
                if meal.recipe_id not in recipes
            ]
        )
```

```python
# diet_domain/nutrition_agent/validators/no_allergens.py
from suvereo_common.agentic_execution import (
    BaseExecutionValidator,
    ExecutionInputType,
    ToolScratchpad,
    ValidatorResponse,
)

from .shared import get_profile, load_recipes, parse_plan, reject


class NoAllergensValidator(BaseExecutionValidator):
    """Checks that no recipe contains an allergen of the user."""

    def validate(
        self, response: str, execution_input: ExecutionInputType, tool_scratchpad: ToolScratchpad
    ) -> ValidatorResponse:
        allergies = set(get_profile(execution_input).allergies)
        plan = parse_plan(response)
        recipes = load_recipes(plan)
        problems = []
        for day in plan.days:
            for meal in day.meals:
                recipe = recipes[meal.recipe_id]
                matched = allergies.intersection(recipe.allergens)
                if matched:
                    problems.append(f"Day {day.day}: '{recipe.title}' contains {', '.join(sorted(matched))}.")
        return reject(problems)
```

```python
# diet_domain/nutrition_agent/validators/calorie_target.py
from suvereo_common.agentic_execution import (
    BaseExecutionValidator,
    ExecutionInputType,
    ToolScratchpad,
    ValidatorResponse,
    ValidatorSuccessResponse,
)

from .shared import get_profile, load_recipes, parse_plan, reject

CALORIE_TOLERANCE = 0.10


class CalorieTargetValidator(BaseExecutionValidator):
    """Checks that each day's calories are within the tolerance of the user's target, when there is one."""

    def validate(
        self, response: str, execution_input: ExecutionInputType, tool_scratchpad: ToolScratchpad
    ) -> ValidatorResponse:
        target = get_profile(execution_input).target_calories
        if not target:
            return ValidatorSuccessResponse()
        plan = parse_plan(response)
        recipes = load_recipes(plan)
        problems = []
        for day in plan.days:
            calories = sum(recipes[meal.recipe_id].calories * meal.servings for meal in day.meals)
            if abs(calories - target) > target * CALORIE_TOLERANCE:
                problems.append(
                    f"Day {day.day}: calories are {calories:.0f} but the target is {target} "
                    f"(allowed deviation {CALORIE_TOLERANCE:.0%})."
                )
        return reject(problems)
```

The package exports them, so that the rest of the domain definition imports from `.validators`:

```python
# diet_domain/nutrition_agent/validators/__init__.py
from .all_days_planned import AllDaysPlannedValidator
from .calorie_target import CalorieTargetValidator
from .meal_plan_json import MealPlanJsonValidator
from .no_allergens import NoAllergensValidator
from .recipes_exist import RecipesExistValidator

__all__ = [
    "AllDaysPlannedValidator",
    "CalorieTargetValidator",
    "MealPlanJsonValidator",
    "NoAllergensValidator",
    "RecipesExistValidator",
]
```

What each validator decides:

| Validator | Checks | On failure |
|---|---|---|
| `MealPlanJsonValidator` | The answer is JSON and has the shape of `MealPlan`. | The model is told what is wrong, field by field, and gets another attempt. |
| `AllDaysPlannedValidator` | Each requested day appears once. | Retry, with the days that were found. |
| `RecipesExistValidator` | Every `recipe_id` exists. | Retry, listing the unknown ids. |
| `NoAllergensValidator` | No recipe contains an allergen of the user. | Retry, listing the recipes and allergens. |
| `CalorieTargetValidator` | Each day's calories are within 10% of the target, if there is one. | Retry, listing the days and their calories. |

- **`MealPlanJsonValidator` overrides `IsValidJsonValidator`**, the validator that every execution has by default. It calls the parent to reject text that is not JSON, then checks the shape. Pydantic reports every problem at once, such as `days.0.meals.0.servings: Input should be greater than 0`, and that list is the feedback.
- **The validators after it call `parse_plan()` without handling errors.** It cannot fail there, because the JSON validator ran first. The same goes for `recipes[meal.recipe_id]` in the last two, which `RecipesExistValidator` guarantees.
- **Every validator that fails lists all of its problems**, so that the model can fix them in one attempt.

Allergens are checked against the recipes' stored `allergens`, not against what the model says about them. That is the point of validating in code: a safety rule does not depend on the model following the prompt. It is only as good as the data it checks, which here is the keyword classifier from the [integrations page](/docs/customization/tutorial/integrations#allergens-and-dietary-tags).

## 4. The definition

The definition ties the pieces together and implements `execute()`, which performs one attempt:

```python
# diet_domain/nutrition_agent/execution_definition.py
from pydantic import Field
from suvereo_agent_tools import StopExecutionTool
from suvereo_common.agentic_execution import (
    BaseAgenticExecutionDefinition,
    ExecutionConversationInterface,
    ExecutionInputType,
    StopExecutionValidator,
)
from suvereo_common.config import LLMToolConfig

from diet_domain.models import UserProfile
from diet_domain.nutrition_agent.tools.serialization import profile_as_dict

from .prompt import WEEKLY_MEAL_PLAN_EXECUTION_PROMPT
from .tools import SearchRecipesTool
from .validators import (
    AllDaysPlannedValidator,
    CalorieTargetValidator,
    MealPlanJsonValidator,
    NoAllergensValidator,
    RecipesExistValidator,
)


class WeeklyMealPlanInput(ExecutionInputType):
    user_id: int = Field(description="Id of the user the plan is made for.")
    days: int = Field(default=7, ge=1, le=14, description="Number of days to plan.")


class WeeklyMealPlanExecutionDefinition(BaseAgenticExecutionDefinition):
    EXECUTION_KEY = "weekly-meal-plan"
    AGENT_KEY = "nutrition-assistant"
    NAME = "Weekly meal plan"
    DESCRIPTION = "Builds a meal plan for a user, validated against their allergies and daily calorie target."
    INPUT_TYPE = WeeklyMealPlanInput
    VALIDATORS = [
        StopExecutionValidator,
        MealPlanJsonValidator,
        AllDaysPlannedValidator,
        RecipesExistValidator,
        NoAllergensValidator,
        CalorieTargetValidator,
    ]
    SYSTEM_PROMPT = WEEKLY_MEAL_PLAN_EXECUTION_PROMPT
    TOOLS = [LLMToolConfig(tool_class=SearchRecipesTool), LLMToolConfig(tool_class=StopExecutionTool)]

    def execute(self, input_data: WeeklyMealPlanInput, conversation: ExecutionConversationInterface) -> str:
        profile = UserProfile.objects.filter(user_id=input_data.user_id).first()
        if profile is None:
            return conversation.ask(
                f"User {input_data.user_id} has no profile, so no plan can be made. Call stop_execution with that reason."
            )
        return conversation.ask(
            f"Build a meal plan for {input_data.days} days for a user with this profile:\n{profile_as_dict(profile)}"
        )
```

`WeeklyMealPlanInput` is the class of step 1, which sits at the top of this file.

| Variable | Meaning |
|---|---|
| `EXECUTION_KEY` | The identifier that API requests use to choose this execution. |
| `AGENT_KEY` | The agent class it runs on. It matches the `AGENT_KEY` of `NutritionAssistantAgent`, so the execution is offered for agents of that type. |
| `NAME`, `DESCRIPTION` | What the UI shows when launching an execution. |
| `INPUT_TYPE` | The input model of step 1. |
| `VALIDATORS` | Run in this order after every attempt. `StopExecutionValidator` ends the execution when the agent called `stop_execution`. The validators of step 3 follow, with the general checks first (JSON and shape), so that each later one can assume what the earlier ones established. |
| `SYSTEM_PROMPT` | Replaces the agent's conversation prompt for this execution. |
| `TOOLS` | The tools of the agent in this execution. A list replaces the agent's own, so it can be a smaller set. Here it is the recipe search and the tool that ends the execution. The profile tools are left out: they act on the user of the conversation, and the caller of an execution may not be the user the plan is made for, whose `user_id` is passed in the input. |

`execute()` is where the domain definition's data enters. The agent runs without a person, so the code loads the profile of the user from the input and puts it in the first message, rather than relying on the model to ask. `conversation.ask()` sends a message to the agent and returns its answer, and the base class passes that answer to the validators. When a validator rejects it, the base class sends the feedback to the model and the retry loop continues.

Export the definition:

```python
# diet_domain/nutrition_agent/__init__.py
from .agent import NutritionAssistantAgent
from .execution_definition import WeeklyMealPlanExecutionDefinition, WeeklyMealPlanInput

__all__ = ["NutritionAssistantAgent", "WeeklyMealPlanExecutionDefinition", "WeeklyMealPlanInput"]
```

## 5. Register the execution

Add it to `server/config/settings_override.py`:

```python
AVAILABLE_AGENTIC_EXECUTION_DEFINITIONS = [
    "diet_domain.nutrition_agent.WeeklyMealPlanExecutionDefinition",
]
```

Rebuild and restart with `docker compose up -d --build`.

## Try it

You need the id of a user that the sample source created, for example `anna.kowalska@example.com`. The list of users, `GET /api/users`, returns the ids.

**From the UI.** Go to **Configure** → **Agentic Executions**, choose **New Execution**, select the nutrition assistant and **Weekly meal plan**, and enter the user id and the number of days. The detail view refreshes while the execution runs. See [Agentic executions](/docs/management/agentic-executions).

**From the API.** List the execution types of the agent to see the input schema generated from `WeeklyMealPlanInput`, then start one. Replace `7` with the id of your agent:

```http
POST /api/agents/7/agentic-executions/
Content-Type: application/json
Authorization: Token <your-token>

{
  "execution_key": "weekly-meal-plan",
  "input": {"user_id": 2, "days": 3}
}
```

The response is `202 Accepted` with the execution in the `pending` state. Poll it until its status is `finished` or `failed`, as described in [Run an Agentic Execution via the API](/docs/connect/agentic-execution-via-api). The token is the API key of a service account that is allowed to run executions, see [Connecting to the API](/docs/connect/connect-to-api).

A finished execution's result is the plan, which passed every validator:

```json
{"days": [{"day": 1, "meals": [{"meal": "breakfast", "recipe_id": 3, "servings": 1.0}]}]}
```

A user with allergies gets a plan without the recipes that contain them, and with calories within 10% of their target on every day. When the model cannot produce such a plan in the allowed number of attempts, the execution ends as `failed` with the code `max_retries_exceeded`, and the explanation says what was wrong. The execution's conversation, linked in the detail view, shows the agent's messages and tool calls.

With only nine sample recipes, a tight calorie target can be hard to meet, and a failed execution is a normal outcome. A larger recipe source makes plans easier, and `CALORIE_TOLERANCE` is the place to adjust the tolerance.

## Where to go from here

The domain definition now has every part described in [Domain definitions](/docs/customization/domain-definitions) and [Integrations](/docs/customization/integrations), and an agent with a conversation and an execution on top of it. To adapt it to your own domain:

- Replace the entities with those of your domain, and write the integration types for the systems that hold them.
- Connect a real system by following [Connecting a real system](/docs/customization/tutorial/integrations#connecting-a-real-system).
- Give the agent more tools, for example tools that read and change the user's profile. A tool reaches such data through the injector, so add it to the injector and the builder first.
- Add more executions to the agent. They share `AGENT_KEY` and differ in `EXECUTION_KEY`.
