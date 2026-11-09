# Evaluate an Agent

An [evaluation](/docs/concepts#evaluation) suite runs your [agent](/docs/concepts#agent) on a set of cases, measures every run and writes reports you can compare across models, prompts and code changes. Each run calls a real LLM and costs a few cents.

This guide evaluates the nutrition assistant built in the [tutorial](/docs/customization/tutorial): its `weekly-meal-plan` [execution](/docs/concepts#agentic-execution), which plans meals for a user and checks every plan against their allergies and calorie target. Finish the tutorial first, so the instance has the assistant, the execution, and the sample recipes and users synced into a [data set](/docs/concepts#data-set).

## How it works

An evaluation answers one question with numbers: how well does this agent do its job, and does a change make it better or worse?

- **A suite** is a directory of plain files you keep next to your code: which agent to run, with which models and prompts, and what to measure. See [Suites and Cases](./suites).
- **Cases** are the inputs the agent gets, each with what a right result looks like. An execution suite gives each case the execution's input; a [conversation suite](./conversations) gives it a dialogue.
- **Metrics** score every run: what the agent produced, how it worked, and what a judge model thinks of it. See [Metrics](./metrics).
- **Mocks** stand in for external systems, so a run can use fixture data and never reaches a real shop or API. See [Mocks](./mocks).
- **Reports** compare every model and prompt side by side, keep a history of runs and give CI an exit code.

A suite runs either an agent you already configured, on its data set as it is, or a new agent in a throwaway data set filled from mocks.

## Before you start

Suites are plain files. Keep them with the [domain definition](/docs/concepts#domain-definition), in `diet-domain/evals/`, one directory per suite:

```text
diet-domain/
├── pyproject.toml
├── diet_domain/
└── evals/
    └── meal_plan/
        ├── suite.yaml
        └── cases.csv
```

Run the commands below from `server/`. The examples use OpenAI models, so set `OPENAI_API_KEY`; any provider listed in `CATALOG_LANGUAGE_MODEL_PROVIDERS` works the same way.

You need two kinds of ids from the instance:

- **The agent's id**: the one in `POST /api/agents/<id>/agentic-executions/` on the tutorial's [last page](/docs/customization/tutorial/agentic-execution#try-it).
- **The sample users' ids**: `GET /api/users` lists them. The tutorial's user source created `anna.kowalska@example.com`, `piotr.nowak@example.com` and `maria.wisniewska@example.com`, each with a profile.

## 1. Write a suite

`suite.yaml` names the agent, the models to run it with and what to measure:

```yaml
name: meal-plan
agent: {id: 7}                           # your nutrition assistant
models: [{provider: OpenAI, model: gpt-4o-mini}]
budget_usd: 0.20                         # stop when this much has been spent
metrics:
  - name: searches
    type: tool_called                    # count calls to a tool
    params: {name: search_recipes}
    pass_threshold: {max: 12}            # a one-day plan needs about four searches
cases: cases.csv
```

`agent: {id: 7}` runs the agent you configured, on its own data set, so the runs plan from the sample recipes and read the sample users' profiles. The agent's stored config stays as it is, and the suite removes the runs' [conversations](/docs/concepts#conversation) afterwards.

`cases.csv` holds one case per row; `input.<field>` columns fill the execution's input. Put in the ids of your sample users:

```csv
id,description,input.user_id,input.days
anna,"Peanut allergy, type 2 diabetes, 1700 kcal",2,1
piotr,"Vegan, 2900 kcal",3,1
maria,"Gluten and dairy allergies, 2100 kcal",4,1
```

## 2. Run it

```shell
./manage.py validateeval ../diet-domain/evals/meal_plan/suite.yaml
./manage.py runeval ../diet-domain/evals/meal_plan/suite.yaml
```

`validateeval` makes no LLM calls: it checks the suite and its cases against the execution's input and prints how many runs it plans. `runeval` runs every case and stops at `budget_usd`.

A run passes when the execution returns a plan and every metric meets its pass threshold. The execution's validators already reject a plan with an allergen or a missed calorie target; the suite adds what they leave open, here how many searches the agent needed.

## 3. Read the results

Each run writes to `<suite>/results/<date>-<id>/`, and `results/latest` points at the newest one:

| File | What it holds |
|---|---|
| `report.md` | The verdict (when the suite sets `min_pass_rate`), a comparison of candidates with a short legend, failures grouped by the pass threshold they missed, with the judge's reasoning and a link to each trace (for a conversation, how it ended, its last turns and a link to its transcript), flaky cases and run details. Start here. |
| `summary.json` | The same verdict and figures for scripts and CI. |
| `results.csv` | One row per run: every metric, whether it met its pass threshold, the judge's reasoning, cost and tokens. |
| `comparison.csv` | One row per candidate (model × prompt variant). |
| `cases.csv` | One row per case and candidate: pass, fail or flaky. |
| `metrics.csv` | One row per run and metric with its details as JSON, for pivots and charts. |
| `runs/*.json` | Each run's metric results and pass thresholds, then its full trace: LLM calls, tool calls, mock calls, attempts. |
| `transcripts/*.md` | In a conversation suite, each run as a readable dialogue: how it ended, the simulated user's goal, persona and facts, and every message with the tools called in its turn. |

The CSVs open directly in a spreadsheet. The exit code tells CI how the run went: `0` every candidate reached the suite's `min_pass_rate` (or it sets none), `1` one fell below it, `2` the suite or an option is invalid, `3` the budget ran out, `4` the run crashed.

The first run shows the kind of thing a suite catches. With nine sample recipes, Anna's 1700 kcal target is tight: a plan that misses it is sent back by `CalorieTargetValidator`, and when the agent cannot fix it within its retries, the run fails with `max_retries_exceeded`. `runs/*.json` shows each attempt with the validator's feedback. A run can also return a valid plan after dozens of searches; `searches` fails it.

## 4. Add a case

YAML cases can sit next to the CSV. Move `cases.csv` into a `cases/` directory, set `cases: cases`, and add a case for a user with no profile:

```yaml
# cases/edge-cases.yaml
- id: unknown-user
  description: A user with no stored profile; the agent must stop instead of planning
  tags: [error-path]
  input: {user_id: 999999, days: 1}
  expected:
    failure_code: validation_failed      # the agent calls stop_execution, which ends the run this way
```

`expected.failure_code` marks a case that should fail: the run passes when the execution fails with that code. The tutorial's execution tells the agent to call `stop_execution` when the user has no profile, and `StopExecutionValidator` ends the execution with `validation_failed`.

## 5. Add a metric

[Metrics](./metrics) explains each built-in metric and how to write your own; `./manage.py listevalmetrics` lists them. A metric with a `pass_threshold` decides whether a run passes; one without is measured and reported only.

A code metric checks what the agent did; a judge reads the run and grades how it worked. This one asks whether the searches excluded the user's allergens:

```yaml
judge: {provider: OpenAI, model: gpt-4.1-mini}  # the model llm_judge asks

metrics:
  - name: searching
    type: llm_judge
    params:
      include: [expected, trace_summary]  # the case's answer key and the tool calls
      criteria:
        - name: excludes_allergens
          description: "Every search_recipes call passes all of the profile's allergies as excluded_allergens"
```

The input holds only a user id, so the case states the profile under `expected` for the judge to compare with:

```yaml
- id: anna
  input: {user_id: 2, days: 1}
  expected:
    profile: {allergies: [peanuts], conditions: [type 2 diabetes], target_calories: 1700}
```

Pick a judge other than the models under test, as a model favours its own answers. The judge explains each score; read its reasoning under each failed run in `report.md`, in the `searching.reasoning` column of `results.csv`, or in `runs/*.json`.

## 6. Compare and iterate

Add a model or a prompt and the report compares them side by side:

```shell
./manage.py runeval suite.yaml --model gpt-4o-mini --model OpenAI:gpt-4.1-nano  # two models
./manage.py runeval suite.yaml --prompt-file my-prompt.txt              # try a prompt without editing the suite
./manage.py runeval suite.yaml --case anna --repeats 3                  # one case, three times
./manage.py runeval suite.yaml --tag error-path                         # the cases with a tag
./manage.py runeval suite.yaml --rerun-failed latest --baseline latest  # only what failed last time
./manage.py runeval suite.yaml --history                                # every run so far, one line each
```

With `--baseline`, `report.md` gains a **Baseline diff**: each candidate's pass rate and metrics before → after, and the cases that regressed or improved. Add `--note "<what you changed>"` to label a run in the history. [Suites and Cases](./suites) builds the full meal-plan suite, with prompt variants, a schema check and per-case metrics.

## 7. Test with fixture data

A suite on your configured agent plans from whatever its data set holds. To test against a fixed set of records, or to try a case on data no real source has, a suite runs the agent in a throwaway data set filled from mocks: `agent: {type: nutrition-assistant}` instead of `{id: ...}`, plus a mock for each [integration](/docs/concepts#integration). [Mocks](./mocks) adds a recipe mock to the domain definition, and [Conversations](./conversations) uses it to test the assistant's chat.

For every option, field and metric, see the [Reference](./reference).
