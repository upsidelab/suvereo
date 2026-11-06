# Suites and Cases

A suite is a directory with a `suite.yaml` and its cases. `suite.yaml` holds what every case shares: the agent, the models to compare, the mocks and the metrics. Each case holds what is specific to one test: the input the agent gets and the right result for it.

```text
diet-vertical/evals/meal_plan/
├── suite.yaml                  # the agent, models, metrics
├── plan.schema.json            # read by the json_schema metric
├── prompts/v2.txt              # a prompt variant to compare
└── cases/
    ├── sample-users.yaml       # several cases in one file
    └── edge-cases.yaml
```

`./manage.py validateeval <suite.yaml>` checks a suite for free and prints the runs it would make; `./manage.py evalschema` prints the JSON Schema of `suite.yaml` for editor completion.

## suite.yaml

The meal-plan suite for the tutorial's nutrition assistant, every line explained:

```yaml
name: meal-plan                        # shown in reports; defaults to the directory name
description: Multi-day meal plans for the sample users, on two prompts

agent: {id: 7}                         # the agent you configured, on its own DataSet

models:                                # the models to run the agent with
  - {provider: OpenAI, model: gpt-4o-mini}
variants:                              # prompts to compare with the agent's own
  - {name: v2, system_prompt_file: prompts/v2.txt}
judge: {provider: OpenAI, model: gpt-4.1-mini}  # the model llm_judge asks

repeats: 1                             # runs per case, model and variant
budget_usd: 0.50                       # stop when this much has been spent
min_pass_rate: 0.8                     # each candidate must pass 80% of its runs
reports: [report, results, comparison, cases]

metrics:                               # what each run is measured on
  - name: plan_shape
    type: json_schema                  # the output is a meal plan
    params: {schema_file: plan.schema.json}
  - name: searches
    type: tool_called                  # search_recipes calls; a day needs about four
    params: {name: search_recipes}
    pass_threshold: {max: 20}
  - name: searching
    type: llm_judge                    # the judge grades the searches against the case's profile
    params:
      include: [expected, trace_summary]
      criteria:
        - {name: excludes_allergens, description: "Every search_recipes call passes all of the profile's allergies as excluded_allergens. Score 1 if the profile has no allergies."}

cases: cases                           # a directory of case files
```

Only `agent`, `metrics` and `cases` are required.

### `agent`

Which agent to test. Set one of:

| Form | Runs |
|---|---|
| `{id: <agent id>}` | An agent you already configured, with its DataSet as it is: the meal-plan suite plans from the synced sample recipes for the sample users. Its stored config stays unchanged, and the runs' conversations are removed afterwards. The suite's mocks replace its integrations; one the suite leaves unmocked runs for real only with `--allow-real-integrations`. |
| `{type: <agent key>}` | A new agent of that type in a throwaway DataSet. The mocks' data, such as fixture recipes, is synced into it, and it is removed after the run (`--keep-run-data` keeps it). See [Mocks](./mocks). |
| `{type: <agent key>, config: {...}}` | The same, with this agent config. |

The agent type must be in `AVAILABLE_AGENTS` and its execution in `AVAILABLE_AGENTIC_EXECUTION_DEFINITIONS`. `execution_key` picks the execution when the agent type has more than one. An agent type with no execution runs as a conversation suite, and `kind: conversation` runs any agent through chat; see [Conversations](./conversations).

### `models`

The models to run the agent with, each `{provider, model}`. Every model is compared with every variant.

| Field | Meaning |
|---|---|
| `provider` | A language model provider's name, e.g. `OpenAI`. |
| `model` | The provider's model name, e.g. `gpt-4o-mini`. |
| `label` | Optional; the name in reports and for `--model`, instead of the model name. |
| `pricing` | Optional; `{input_per_million, output_per_million, cached_input_per_million}` in USD, for a model the bundled price table lacks. |

A provider is usable once its model plugin is installed and listed in `CATALOG_LANGUAGE_MODEL_PROVIDERS`; `validateeval` names the installed ones when a suite asks for another.

Left empty, the DataSet's configured model runs. `--model gpt-4o-mini` runs one of them, and `--model OpenAI:gpt-4.1-nano` adds one without editing the suite.

### `variants`

Changes to compare against the agent as it is, which runs as the `default` variant. Each needs a `name` and one or both of:

| Field | Meaning |
|---|---|
| `system_prompt_file` | A file, relative to the suite, that replaces the system prompt. |
| `agent_config` | Merged over the agent's config, e.g. `{tools: {...}}`; lists are replaced whole. |

A **candidate** is one model and one variant, shown as `gpt-4o-mini/v2`. `--prompt-file my-prompt.txt` tries a prompt as an extra variant without editing the suite.

The meal-plan suite's `prompts/v2.txt` is the tutorial's `WEEKLY_MEAL_PLAN_EXECUTION_PROMPT` with two rules added: it asks the agent to search once per meal type and to add up each day's calories before answering. Running both variants shows whether that helps: the comparison table gives each one's pass rate, searches and cost side by side.

### `judge`

The model `llm_judge` and `llm_classify` ask, and in a conversation suite the one deciding `goal_reached`, `{provider, model}` like a model. Pick one other than the models under test, as a model favours its own answers. A metric can name its own with `params.judge`. The judge's cost is reported as `judge_cost_usd`, apart from the agent's.

### `user_model`

The model playing simulated users in a conversation suite, `{provider, model}` like a model; see [Conversations](./conversations). Its cost is reported as `user_cost_usd`.

### Run size and limits

| Field | Meaning | Default |
|---|---|---|
| `repeats` | Runs per case, model and variant. Above 1, cases whose repeats disagree show as flaky. | 1 |
| `budget_usd` | The run stops once this much is spent, agent, judge and simulated users together, and is marked partial (exit code 3). `--budget` overrides it. | no limit |
| `min_pass_rate` | The share of runs each candidate must pass, 0–1. With it, `report.md` opens with a verdict and a candidate below it makes the run exit 1. Without it the run only reports. | none |

A run passes when it meets every required pass threshold of its metrics, see [Metrics](./metrics). In an execution suite it must also end the way the case expects: with a result, or with the case's `expected.failure_code`.

### `reports`

What to write to `results/<date>-<id>/` besides `summary.json`, which is always written: `report`, `results`, `comparison`, `cases`, `metrics`, `traces` and, for a conversation suite, `transcripts`. The default is `report` and `results`; `--reports` overrides it. [Getting started](./getting-started#2-read-the-results) says what each holds.

### `integrations`

The mocks standing in for every system the agent reaches, each with `class` (a mock integration) or `interface` (a mock built from YAML alone), and a `config` with the mock's `data` and per-method `behaviour`. Paths in `data` are relative to the suite. The meal-plan suite needs none: its agent's DataSet already holds the recipes, and the execution reaches no external system. See [Mocks](./mocks).

### `metrics`

What every run is measured on, each with a `type`, a `name`, `params` and an optional `pass_threshold`. See [Metrics](./metrics).

### `cases`

Where the cases are, relative to the suite:

| Form | Reads |
|---|---|
| `cases: cases` | Every `.yaml`, `.yml` and `.csv` file directly in that directory, in name order. |
| `cases: cases.csv` | One file. |
| `cases: [cases.csv, extra/]` | Several files and directories. |
| `cases: [{id: smoke, input: {...}, expected: {...}}]` | Cases written inline in the suite. |

Case ids must be unique across the suite. `--case <id>` and `--tag <tag>` run a few of them.

## A case

A YAML case file holds one case, or a list of them:

```yaml
- id: anna                             # unique; names the case in reports and for --case
  description: Peanut allergy, type 2 diabetes and a low calorie target   # shown with its failed runs
  tags: [allergy]                      # groups cases; --tag allergy runs them
  input:                               # the execution's input, checked against its input type
    user_id: 2                         # anna.kowalska@example.com on your instance
    days: 3
  expected:                            # her stored profile, for the judge to compare with
    profile:
      allergies: [peanuts]
      conditions: [type 2 diabetes]
      dietary_preferences: [low carb]
      disliked_foods: [mushrooms]
      target_calories: 1700
```

The weekly-meal-plan execution takes the `user_id` of a user with a stored profile and plans for that profile. `GET /api/users` gives the ids of the sample users; they differ between instances, so set them once in the case files. The execution's validators check the plan against the stored profile, so a run with an allergen or a missed calorie target is sent back and, after its retries, fails.

The input names only the user, so the profile is restated under `expected`. The suite's `llm_judge` includes `expected` and grades the searches against it, see [Metrics](./metrics#llm_judge).

| Field | Meaning |
|---|---|
| `id` | Unique across the suite. |
| `description`, `tags` | Shown with the case's failed runs; tags also select cases with `--tag`. |
| `files` | Attached to the conversation, relative to the case file: PDFs and images (`.png`, `.jpg`). |
| `input` | The execution's input fields, checked against its input type. |
| `user_messages`, `simulated_user` | In a conversation suite, the user's side of the dialogue in place of `input`; see [Conversations](./conversations). |
| `expected` | What the metrics compare the run with, see below. |
| `integrations` | Changes to the suite's mocks for this case only. |
| `metrics` | Metrics added for this case, or replacing the suite's metric of the same `name`. |

### `expected`

Each metric reads the part it needs:

| Path | Read by | Meaning |
|---|---|---|
| `expected.output.<field>` | `json_subset`, `field_match`, `list_match` | Fields the agent's answer should contain. |
| `expected.mock_calls.<method>` | `mock_calls` | The calls a mock should receive, one entry per call. An empty list expects none. |
| `expected.failure_code` | `execution_succeeded` | The run should fail with this code, e.g. `validation_failed`; it then passes by failing that way. |
| anything else | `llm_judge`, `llm_classify`, your own metrics | Facts about the case, such as the profile above; a judge sees them with `include: [expected]`. |

A case with nothing at a metric's path gives that metric no value, which misses its pass threshold. Add such a metric only to the cases that give it a value, as `piotr` does below.

A case the agent must refuse names the failure it expects:

```yaml
- id: unknown-user
  description: A user with no stored profile; the agent must stop instead of planning
  tags: [error-path]
  input: {user_id: 999999, days: 1}
  expected:
    failure_code: validation_failed    # the agent calls stop_execution, which ends the run this way
```

### Changing a metric or a mock for one case

`piotr` needs a check the other cases have no use for:

```yaml
- id: piotr
  description: A vegan with a high calorie target
  tags: [diet]
  input: {user_id: 3, days: 2}
  expected:
    profile: {dietary_preferences: [vegan], disliked_foods: [cilantro], target_calories: 2900}
  metrics:                             # a new name, so this metric is added for this case
    - {name: follows_diet, type: diet_vertical.evaluation.FollowsDiet, pass_threshold: {equals: true}}
```

**`metrics`** replace the suite's metric with the same `name`, or are added when the name is new. `follows_diet` is a metric you add to the vertical; [Metrics](./metrics#add-your-own-metric) shows its code.

In a sandbox suite, a case can also change the mock data. This case from the [chat suite](./conversations) swaps the recipes for a catalog where every breakfast has dairy:

```yaml
- id: no-dairy-free-breakfast
  description: Every breakfast has dairy; the assistant must say so instead of suggesting one
  user_messages:
    - I'm allergic to dairy. What could I have for breakfast?
    - No other allergies or preferences, and no calorie target.
  integrations:                        # same class as in the suite, so this changes that mock
    - class: diet_vertical.evaluation.RecipeMockIntegration
      config: {data: {recipes: dairy-breakfasts.yaml}}
  expected: {outcome: "Says it found no dairy-free breakfast and suggests no recipe with dairy"}
```

**`integrations`** apply to the suite's mock with the same `class` or `interface`. `config` is merged into the suite's, and a method's `behaviour` replaces the suite's for that method. Cases whose mock data differs run in a sandbox of their own, so this case searches its five recipes while the other cases search the full fixture catalog.

## Cases in a CSV

Simple cases fit one row each, which suits many users. The meal-plan cases as rows:

```csv
id,description,tags,input.user_id,input.days,expected.profile
anna,"Peanut allergy, type 2 diabetes, 1700 kcal",allergy,2,3,"{""allergies"": [""peanuts""], ""target_calories"": 1700}"
maria,"Gluten and dairy allergies, 2100 kcal",allergy,4,2,"{""allergies"": [""gluten"", ""dairy""], ""target_calories"": 2100}"
piotr,"Vegan, 2900 kcal",diet,3,2,"{""dietary_preferences"": [""vegan""], ""target_calories"": 2900}"
```

- `id`, `description`, `tags` and `files` are columns; separate several tags or files with `;`, or write them as a JSON list.
- `input.<field>` and `expected.<dotted.path>` columns build those mappings; a number in the path indexes a list, so `expected.mock_calls.create_order.0.items` is the first call's items.
- A cell starting with `[`, `{` or `"` is read as JSON; anything else stays text. A number such as `2` in `input.user_id` is checked against the input type, which turns it into a number.
- Any other column reaches custom metrics as `case.extra`.

A case needing its own mocks or metrics goes in a YAML file; YAML and CSV cases can sit in the same directory.
