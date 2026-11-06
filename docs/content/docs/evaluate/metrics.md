# Metrics

A metric measures one thing about every run: a **number**, a **bool** or a **label**. Some are measured on every run with no config; the rest you add under `metrics` in `suite.yaml`, or in a case to add or replace one for that case. `./manage.py listevalmetrics` lists them all with their params.

This metric, from the meal-plan suite for the tutorial's nutrition assistant, checks that the nutrition assistant found its recipes without searching in circles:

```yaml
metrics:
  - name: searches                 # column name in the reports
    type: tool_called              # the built-in metric to run
    description: search_recipes calls; a day needs about four  # shown in the report.md legend
    params: {name: search_recipes} # count calls to this tool
    pass_threshold: {max: 20}      # a run passes with at most 20 calls
    required: true                 # a miss fails the run; false only warns
```

| Field | Meaning |
|---|---|
| `type` | Which metric to run: a built-in below, or the dotted path of your own. |
| `name` | Your name for this check; reports use it as the column header. Optional when the type is used once, then the type is the name. |
| `description` | A few words on what it checks, shown in the `report.md` legend. |
| `params` | The metric's settings; here, which tool to count. |
| `pass_threshold` | The value a run needs to pass, e.g. `{equals: 1}`, `{min: 0.95}`, `{max: 3}`. Without it the metric is only reported. |
| `required` | `true` (the default) fails the run on a miss; `false` only warns. |

A metric that cannot measure a run, such as a case with no expected value for it, records no value and the reason in its details. A run with no value misses that metric's pass threshold.

## Measured on every run

| Metric | Value | Measures |
|---|---|---|
| `execution_succeeded` | bool | The run succeeded; for a case with `expected.failure_code`, it failed with that code |
| `failure_code` | label | The run's failure code, `RUNTIME_ERROR` when it raised, none when it succeeded |
| `attempts` | number | Attempts the validator loop took |
| `first_attempt_success` | bool | The right outcome without the validator sending the agent back |
| `duration_s` | number | Wall-clock seconds |
| `cost_usd` | number | The agent's LLM cost in USD, nested calls included; the judge's is `judge_cost_usd` |
| `input_tokens`, `output_tokens` | number | Tokens over every LLM call |
| `llm_calls`, `tool_calls` | number | LLM calls and tool calls the run made |

A conversation suite measures `conversation_completed`, `conversation_end`, `turns`, `goal_reached` and `user_cost_usd` in place of the first four; see [Conversations](./conversations#what-a-run-measures).

Give one a `pass_threshold` by adding it to `metrics` under its own name, e.g. `{type: cost_usd, pass_threshold: {max: 0.01}}`.

## What the agent produced

These compare the run's output, or what reached the mocks, with the case's `expected`. The nutrition assistant's output is a meal plan of recipe ids, which `json_schema` and your own `follows_diet` check best; the examples for the other metrics use the answers of other agents.

### `json_subset`

The share of fields under `expected.output` that the output matches, 0–1. Fields the case leaves out are skipped, so each case names only the fields it cares about. Take an agent that answers with one recommended recipe:

```yaml
# suite.yaml
- name: answer
  type: json_subset
  params:
    modes:                      # how to compare a field; any field not listed must be equal
      calories: "numeric:10"    # a number within 10 of the expected one
      recipe.title: ci          # the same text, ignoring upper/lower case
    coerce: true                # "540" vs 540 count as equal
  pass_threshold: {min: 1}      # every expected field must match
```

```yaml
# a case: the fields it checks
expected:
  output:
    meal_type: main
    calories: 540
    recipe: {title: lentil and spinach curry}
```

If the agent answers `{"meal_type": "main", "calories": "545", "recipe": {"title": "Lentil and Spinach Curry", "id": 11}, "notes": "..."}`, all three fields match: `calories` is within 10, `recipe.title` differs only in case, and `id` and `notes` are not checked. The value is 1. With `"meal_type": "snack"` it would be 2 of 3, 0.67, and the run would miss `{min: 1}`.

| Param | Meaning | Values | Default |
|---|---|---|---|
| `modes` | How to compare particular fields. Each key is a field's dotted path (`total`, `customer.name`), each value a [match mode](#match-modes). Fields left out are compared `exact`. | `exact`, `ci`, `numeric`, `numeric:<tolerance>`, `fuzzy`, `fuzzy:<threshold>`, `regex` | every field `exact` |
| `coerce` | Treat a number and its text as equal, so `"540"` matches `540`. Applies to `exact` fields. | `true`, `false` | `false` |
| `path` | Check only one part of the output. `path: recipe` compares `output.recipe` with `expected.output.recipe`; `modes` keys are then relative to it (`title`, not `recipe.title`). | a dotted path | the whole output |

- Each leaf is a field: `recipe: {title: ...}` is `recipe.title`; a list is one field and must match whole.
- `mismatched` in the details lists each field that missed, with `expected` and `actual`; `actual` is `null` when the output has no such field.
- `{min: 1}` needs every field, `{min: 0.5}` half of them.

### `field_match`

Whether one output field matches its expected value; bool.

```yaml
- name: meal
  type: field_match
  params:
    path: meal_type # output.meal_type is compared with expected.output.meal_type
    mode: ci        # the same text, ignoring upper/lower case
```

Params: `path` in the output, `expected_path` under `expected.output` (defaults to `path`), `mode`, `coerce`.

### `list_match`

F1 of an output list against the expected one, 0–1, with precision and recall as components.

An agent that answers with a shopping list for a plan, `{"items": [{"ingredient": "red lentils", "grams": 300}, ...]}`:

```yaml
- name: shopping_list
  type: list_match
  params:
    path: items                # the list in the output, compared with expected.output.items
    key: ingredient            # an output item and an expected one are the same when their ingredient is equal
    fields: {grams: "numeric:20"} # then their grams must be within 20
    coerce: true               # "300" and 300 count as equal
  pass_threshold: {min: 0.95}  # nearly every item right, none extra
```

`key` pairs actual items with expected ones by one field (or index, for lists such as `[sku, quantity]`), and `fields` checks the others with a match mode each. Without `key`, whole items are compared. The details list `missing`, `extra` and `mismatched` items.

**F1** is one 0–1 score for how well a list matches the expected one. It combines two questions:

- **Precision**: of the items the agent gave, how many are right? Extra or wrong items lower it.
- **Recall**: of the items expected, how many did the agent give? Missing items lower it.

F1 is their balance, 1 only when both are 1. For example, if 4 items are expected and the agent gives 3 of them plus 1 that is not expected, precision is 3/4, recall is 3/4 and F1 is 0.75. An item with the right key but a wrong field, such as the right ingredient with the wrong weight, counts as both missing and extra.

### `mock_calls`

F1 of what reached a mock against `expected.mock_calls.<method>`, 0–1. It scores what the agent sent to the outside system, whatever its output says. It suits agents that call an integration at runtime, such as Enthusiast's order-intake agent and its mocked shop (see [Mocks](./mocks#mocking-the-calls-an-agent-makes)):

```yaml
# suite.yaml
- name: line_items
  type: mock_calls
  params:
    method: create_order_with_items # the mocked shop method to read
    arg: items                      # the argument to score, here a list of [sku, quantity]
    key: 0                          # pair items by position 0 of each pair, the sku
    fields: {1: numeric}            # then position 1, the quantity, must be the same number
    coerce: true                    # "6" and 6 count as equal
    skip_failed: true               # ignore orders the shop rejected
  pass_threshold: {min: 0.95}
```

```yaml
# a case: the order the shop should receive
expected:
  mock_calls:
    create_order_with_items:
      - items: [[MUG-RED, 6], [TEA-GRN, 2]]
```

- With `arg`, the i-th call's argument is scored against the i-th expected call's, item by item when it is a list.
- Without `arg`, each call's arguments are one item and the calls are scored as a list in any order, e.g. one `update_stock` call per SKU with `key: sku`.
- `skip_failed: true` leaves out calls the mock rejected, so a call the agent fixed and sent again counts once.
- An empty expected list expects no calls.

### `json_schema`

Whether the output conforms to a JSON Schema; bool. Set `schema` inline or `schema_file` relative to the suite. The details list the first five errors.

The meal-plan suite checks every output has the shape of a plan:

```yaml
- name: plan_shape
  type: json_schema
  params:
    schema_file: plan.schema.json # next to suite.yaml; or schema: {...} inline
```

## How the agent worked

These read the trace: the tools the agent called, the mock calls and the validator loop.

### `tool_called`

How many times the agent called a tool; a number. `args` counts only calls with those argument values.

```yaml
- name: snack_searches
  type: tool_called
  params:
    name: search_recipes       # the tool to count
    args: {meal_type: snack}   # optional; counts only the calls with these arguments
  pass_threshold: {min: 1}     # looked for snacks at least once
```

### `tool_not_called`

Whether the agent never called a tool; bool.

```yaml
- name: planned
  type: tool_not_called
  params:
    name: stop_execution       # passes when the agent planned instead of stopping
```

### `tool_order`

Whether the agent called tools in this order; bool. Other calls may come in between, or none with `strict: true`. A miss lists the calls in `called`.

```yaml
- name: profile_first
  type: tool_order
  params:
    sequence: [get_user_profile, search_recipes] # read the user's profile before searching
    strict: false              # other calls may come in between
```

This one belongs in the chat suite: the assistant has `get_user_profile` in a conversation, and the meal-plan execution gets the profile in its first message.

### `mock_called`

How many times a mocked method was called; a number. `args` counts only calls with those argument values. Like `mock_calls`, it reads an integration the agent calls at runtime, here Enthusiast's shop.

```yaml
- name: orders
  type: mock_called
  params:
    method: create_order_with_items # the mocked shop method to count
  pass_threshold: {max: 1}     # at most one order reached the shop
```

### `trace_event`

Whether something happened during the run; bool. `event` is one of `retry`, `tool_error`, `validator_failed`, `validator_failed:<code>` or `stop_execution`.

```yaml
- name: retried
  type: trace_event
  params:
    event: retry               # the validator sent the agent back at least once
  pass_threshold: {equals: false} # a run without a retry is the goal
  required: false              # a retry only warns
```

## Judged by a model

These ask the suite's `judge` model, or the metric's own `judge`, about the run. `include` picks what it sees: `input`, `outcome`, `output`, `expected`, `trace_summary` and, in a conversation, `transcript`, each user message and answer with what each tool called in that turn returned, or the error it raised. In a conversation the judge grades the agent's messages. `prompt` or `prompt_file` replaces the built-in prompt; it must contain `{material}`, where the run details go. A run that raised before the agent answered gets no value and no judge call. What the judge costs is reported as `judge_cost_usd`.

### `llm_judge`

Grades the run against criteria you write, 0–1. Each criterion is asked separately and reported as a component with the judge's reasoning; the value is their weighted average.

```yaml
- name: searching
  type: llm_judge
  params:
    include: [expected, trace_summary] # the case's profile and the tool calls
    scale: binary              # each criterion is met (success) or not (failure)
    criteria:                  # each one is asked separately and scored on its own
      - name: excludes_allergens
        description: "Every search_recipes call passes all of the profile's allergies as excluded_allergens"
        weight: 2              # counts twice in the average
      - name: fits_profile
        description: "The search queries reflect the profile's conditions and preferences, e.g. low carb for diabetes"
```

| Param | Meaning | Values | Default |
|---|---|---|---|
| `criteria` | What to grade. Each has a `name` (its column in the reports), a `description` the judge reads, and an optional `weight` in the average. | a list, at least one | – |
| `scale` | How the judge scores each criterion; see below. | `binary`, `"1-5"`, `{min, max}` | `binary` |
| `include` | What the judge sees of the run. | `input`, `outcome`, `output`, `expected`, `trace_summary`, `transcript` | `outcome`, `output`, `expected`; in a conversation `outcome`, `transcript`, `expected` |
| `samples` | How many times each criterion is asked; the median score is kept. | 1–9 | 1 |
| `judge` | A model for this metric instead of the suite's `judge`. | `{provider, model}` | the suite's |
| `prompt`, `prompt_file` | Your own prompt instead of the built-in one; it must contain `{material}`. | text, or a file next to the suite | built-in |

**Scales.** Each score is turned into 0–1, so different scales still average the same way:

| `scale` | The judge answers | In the reports |
|---|---|---|
| `binary` | 0 (not met) or 1 (met) | `fits_profile (failure)` / `(success)` |
| `"1-5"` | 1 (not met at all) to 5 (fully met); 4 becomes 0.75 | `fits_profile 0.75` |
| `{min: 0, max: 10}` | any number in your range; 7 becomes 0.7 | `fits_profile 0.7` |

```yaml
    scale: "1-5"               # each criterion scored 1 to 5
    samples: 3                 # wider scales vary between runs; the median of 3 steadies them
```

Binary scores are the most consistent between runs. A wider scale tells partly-met from not-met, but a judge's 3 against 4 is noisy, so pair it with `samples: 3`, which triples the judge's cost.
- Code metrics check what the agent produced; a judge suits how it worked. Write each criterion so it can be scored from what `include` shows, and say how to score the cases it does not apply to, e.g. "Score 1 if the profile has no allergies."
- The judge reads tool results shortened, so let it grade what the calls show, such as the arguments of each search, and leave counts to code metrics: in the meal-plan suite, `searches` counts the calls and the judge grades how they were made.

### `llm_classify`

Asks one question and records which of your labels the judge answered; a label. Labels aggregate as counts per candidate.

```yaml
- name: stop_reason
  type: llm_classify
  params:
    question: Why did the agent stop instead of planning?   # asked of the judge model
    labels: [no_profile, no_safe_recipe, calorie_target, none] # it must answer with one of these
```

## Match modes

A match mode says how an actual value is compared with the expected one. `field_match` takes one as `mode`; `json_subset` takes one per field as `modes`; `list_match` and `mock_calls` take one per item field as `fields`.

| Mode | Matches when | Expected | Matches | Doesn't match |
|---|---|---|---|---|
| `exact` | The values are equal; with `coerce: true` a number equals its text | `3` | `3` (`"3"` with `coerce`) | `3.0001`, `"three"` |
| `ci` | Case-insensitive: the text is equal, ignoring upper/lower case and extra spaces | `fruit salad` | `Fruit  Salad` | `Fruit bowl` |
| `numeric` | The numbers are equal; numbers given as text count | `540` | `"540"`, `540.0` | `539` |
| `numeric:<tolerance>` | The numbers differ by at most the tolerance | `1700` with `numeric:50` | `1712` | `1800` |
| `fuzzy` | The texts are at least 85% similar | `Vegan chia pudding` | `Vegan chia puding` | `Rice pudding` |
| `fuzzy:<threshold>` | The texts are at least this similar, 0–1 | `Bean chili with rice` with `fuzzy:0.7` | `bean chilli & rice` | `Beef stir-fry` |
| `regex` | The expected value, as a regular expression, matches the whole actual value | `b-\w+` | `b-chia` | `m-lentil` |

Quote a mode with a colon in YAML (`"numeric:50"`) when it is a flow value; on its own line it works as is.

## Add your own metric

Subclass `BaseMetric` anywhere importable and set `type` to its dotted path. Declare `NAME`, `VALUE_TYPE` (`number`, `bool` or `label`) and, for params, a Pydantic model as `PARAMS`; `measure` gets the run and returns a `MetricResult`.

`FollowsDiet` checks what the tutorial's validators leave open: that a vegan or vegetarian gets only vegan or vegetarian recipes. Add it to the vertical, in `diet_vertical/evaluation/follows_diet.py`, next to the [recipe mock](./mocks):

```python
from suvereo_common.evaluation.metrics import BaseMetric, MetricContext, MetricResult

from diet_vertical.models import UserProfile
from diet_vertical.nutrition_agent.validators.shared import MealPlan, load_recipes
from diet_vertical.structures import DietaryTag


class FollowsDiet(BaseMetric):
    """Whether every planned recipe is vegetarian or vegan when the user's profile asks for that diet."""

    NAME = "follows_diet"
    VALUE_TYPE = "bool"

    def measure(self, context: MetricContext) -> MetricResult:
        profile = UserProfile.objects.filter(user_id=context.case.input.get("user_id")).first()
        preferences = profile.dietary_preferences if profile else []
        diets = [tag for tag in DietaryTag if tag.value in preferences]
        if not diets:
            return MetricResult(value=None, details={"reason": "the profile asks for no vegetarian or vegan diet"})
        if context.trace.output is None:
            return MetricResult(value=None, details={"reason": "the run produced no plan"})
        plan = MealPlan.model_validate(context.trace.output)
        recipes = load_recipes(plan)
        off_diet = [
            f"Day {day.day}: {recipes[meal.recipe_id].title} is not {diet}"
            for day in plan.days
            for meal in day.meals
            if meal.recipe_id in recipes
            for diet in diets
            if diet not in recipes[meal.recipe_id].dietary_tags
        ]
        return MetricResult(value=not off_diet, details={"off_diet": off_diet} if off_diet else {})
```

```yaml
- name: follows_diet
  type: diet_vertical.evaluation.FollowsDiet # the dotted path of your class
  pass_threshold: {equals: true}
```

It reads the stored profile of the case's user and the plan from the run's output, and looks the planned recipes up with the tutorial's `load_recipes`, as the validators do. A user with no vegetarian or vegan preference gives it nothing to measure, so the meal-plan suite adds it only to `piotr`.

A metric with settings declares them as a Pydantic model in `PARAMS`, available as `self.params`:

```python
from pydantic import BaseModel, ConfigDict
from suvereo_common.evaluation.metrics import BaseMetric, MetricContext, MetricResult


class SearchesParams(BaseModel):
    model_config = ConfigDict(extra="forbid")

    per_day: int = 4


class SearchesPerDay(BaseMetric):
    """search_recipes calls per planned day."""

    NAME = "searches_per_day"
    VALUE_TYPE = "number"
    PARAMS = SearchesParams

    def measure(self, context: MetricContext) -> MetricResult:
        days = context.case.input.get("days", 7)
        searches = len(context.trace.tool_calls_named("search_recipes"))
        return MetricResult(value=searches / days, details={"budget": self.params.per_day * days})
```

- **`context`** holds the `trace` (`output`, `tool_calls`, `mock_calls`, `llm_calls`, `attempts`, `error`, and for a conversation its `turns` and `stop_reason`, with helpers such as `tool_calls_named`, `mock_calls_to` and `tool_calls_in(turn)`), the `case` (`expected` and `extra` for other CSV columns, plus `input` in an execution suite, or `user_messages` and `simulated_user` in a conversation suite), the suite's `kind` (`execution` or `conversation`), `duration_s`, `cost_usd` and the `judge` client.
- **`MetricResult`** takes the `value`, `details` that `report.md` lists under a missed threshold, and `components`, numbers that get their own `results.csv` columns; `binary_components=True` shows them as success or failure.
- **No value:** return `value=None` with a `reason` when the case gives nothing to measure. An exception is caught and recorded as the metric's `error`; the other metrics still run.
- **Params** are validated when the suite loads, so `validateeval` reports a typo before any run. A relative path in params resolves against the suite directory through the validation context key `base_dir`.
- **Matching:** `ValueMatcher`, `ListScorer` and `DottedPath` from `suvereo_common.evaluation.metrics.matching` give your metric the match modes and list scoring the built-ins use.
