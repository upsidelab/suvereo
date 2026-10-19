---
sidebar_position: 5
---

# Evaluation Reference

## Commands

| Command | What it does |
|---|---|
| `./manage.py runeval <suite.yaml>` | Runs the suite and writes its reports. |
| `./manage.py validateeval <suite.yaml>` | Checks the suite, its cases, mocks and metrics, and prints the planned run count. Free. |
| `./manage.py evalschema` | Prints the JSON Schema of `suite.yaml`, for editor completion. |
| `./manage.py listevalmetrics` | Lists the built-in metrics with their value types and params. |

### `runeval` options

| Option | What it does |
|---|---|
| `--model M` | Runs this suite model (by label) or any `Provider:model`. Repeatable. |
| `--variant V` | Runs this variant besides the default. Repeatable. |
| `--prompt-file F` | Adds the file as a system prompt variant named after the file. |
| `--case ID`, `--tag T` | Runs these cases, or the cases with this tag. Repeatable. |
| `--rerun-failed S` | Runs the cases that failed in a `summary.json`, a run directory or `latest`. |
| `--repeats N` | Runs per case, model and variant. |
| `--baseline S` | Adds a diff against an earlier run (`summary.json`, a run directory or `latest`). |
| `--budget USD` | Stops starting runs once this much is spent; overrides `budget_usd`. |
| `--parallel N` | Runs this many at once (default 1). |
| `--reports a,b` | Writes these reports; overrides `reports`. |
| `--note TEXT` | Recorded with the run in the history, e.g. what you changed. |
| `--format json` | Prints `summary.json` to stdout; logs go to stderr. |
| `--history` | Prints the suite's earlier runs and exits. |
| `--allow-real-integrations` | Lets an existing agent's unmocked integrations run for real. |
| `--keep-run-data` | Keeps the sandbox DataSet and conversations for inspection. |

### Exit codes

| Code | Meaning |
|---|---|
| `0` | Every candidate reached `min_pass_rate`, or the suite sets none. |
| `1` | At least one candidate is below `min_pass_rate`. |
| `2` | The suite or an option is invalid. |
| `3` | The run stopped early, at the budget or at a call it had no price for; it is marked partial. |
| `4` | The run crashed. |

## Suite

Only `agent`, `metrics` and `cases` are required. [Suites and Cases](./suites) walks through each field with examples.

| Field | Meaning |
|---|---|
| `name`, `description` | The name defaults to the suite's directory name. |
| `agent` | `{type: <agent key>, config: {...}}` runs in a throwaway sandbox DataSet; `{id: N}` runs an existing agent. |
| `execution_key` | The agentic execution to run; needed only when the agent type has several. |
| `integrations` | The mocks, see [Mocks](./mocks). |
| `models` | `{provider, model, label, pricing}` each. Left empty, the DataSet's configured model runs. |
| `variants` | `{name, system_prompt_file}` and/or `{name, agent_config}`, each compared against `default`, the agent's own prompt. `agent_config` is deep-merged over the agent's config; lists are replaced whole. |
| `judge` | The model `llm_judge` and `llm_classify` ask. |
| `repeats` | Runs per case, model and variant (default 1). |
| `budget_usd` | Spending limit for a run. |
| `min_pass_rate` | Minimum pass rate per candidate, e.g. `0.8`. With it, `report.md` opens with a verdict and a candidate below it exits `1`; without it the run reports its results and gives no verdict. |
| `metrics` | Measured on every case. |
| `reports` | Any of `report`, `results`, `comparison`, `cases`, `metrics`, `traces` (default `report`, `results`). `summary.json` is always written. |
| `cases` | A case file, a directory of them, inline cases, or a list of these. |

A **candidate** is one model and variant, shown as `<model label>/<variant>`. A model's `pricing` (`input_per_million`, `output_per_million`, `cached_input_per_million`) overrides the bundled price table for that model.

## Cases

| Field | Meaning |
|---|---|
| `id` | Unique across the suite. |
| `description`, `tags` | Shown with the case's failed runs in `report.md`; tags also select cases with `--tag`. |
| `files` | Attached to the conversation, relative to the case file: PDFs and images (`.png`, `.jpg`). |
| `input` | The execution's input fields. |
| `expected` | What metrics compare against, see below. |
| `integrations` | Overrides of the suite's mocks: `config` is deep-merged, and a method's behaviour replaces the suite's. |
| `metrics` | Added to the suite's, or replacing one of the same `name`. |

`expected` follows these conventions:

- `expected.output.<field>`: the execution's output, read by `json_subset`, `field_match` and `list_match`.
- `expected.mock_calls.<method>[i].<arg>`: the arguments of a mock's i-th call, read by `mock_calls`. An empty list expects no calls.
- `expected.failure_code`: the run should fail with this code; `execution_succeeded` then checks for that failure.

In `cases.csv` each row is a case: `id`, `description`, `tags` and `files` (`;`-separated), `input.<field>`, `expected.<dotted.path>` (numbers index lists), and any other column, which reaches custom metrics as `case.extra`. A cell starting with `[`, `{` or `"` is parsed as JSON; any other cell stays text. CSV and YAML cases can be mixed; ids must be unique.

## Metrics

Every metric config takes `type`, `name` (defaults to the type; required to use a type twice), `description` (what it checks in plain words; `report.md` explains its column with it), `params`, `pass_threshold`, `required` and `aggregate`.

**Measured on every run**, with no config:

| Metric | Value | Measures |
|---|---|---|
| `execution_succeeded` | bool | The run succeeded, or failed with `expected.failure_code` |
| `failure_code` | label | The run's failure code; none when it succeeded |
| `attempts` | number | Attempts the validator loop took |
| `first_attempt_success` | bool | The right outcome without a validator retry |
| `duration_s` | number | Wall-clock seconds |
| `cost_usd` | number | The agent's LLM cost in USD; the judge's is `judge_cost_usd` |
| `input_tokens`, `output_tokens` | number | Tokens over every LLM call |
| `llm_calls`, `tool_calls` | number | LLM calls and tool calls the run made |

**Set in the suite** with `type`:

| Type | Value | Measures | Params |
|---|---|---|---|
| `json_subset` | 0–1 | Share of `expected.output` fields the output matches, see [Metrics](./metrics#json_subset) | `path`, `modes` per field, `coerce` |
| `field_match` | bool | One output field against its expected value | `path`, `expected_path`, `mode`, `coerce` |
| `list_match` | 0–1 | F1 of an output list against the expected one | `path`, `expected_path`, `key`, `fields`, `coerce` |
| `mock_calls` | 0–1 | F1 of what reached a mock against `expected.mock_calls`; without `arg`, of the calls themselves in any order | `method`, `arg`, `key`, `fields`, `coerce`, `skip_failed` |
| `json_schema` | bool | The output conforms to a JSON Schema | `schema` or `schema_file` |
| `tool_called` | count | Times the agent called a tool, optionally with given arguments | `name`, `args`, `coerce` |
| `tool_not_called` | bool | The agent never called a tool | `name` |
| `tool_order` | bool | The agent called tools in this order | `sequence`, `strict` |
| `mock_called` | count | Times a mocked method was called, optionally with given arguments | `method`, `args`, `coerce` |
| `trace_event` | bool | Something happened during the run | `event`: `retry`, `tool_error`, `validator_failed[:code]` or `stop_execution` |
| `llm_judge` | 0–1 | A judge model grades the run against criteria you write | `criteria` (`name`, `description`, `weight`), `scale` (`binary`, `1-5` or `{min, max}`), `include`, `samples`, `prompt`/`prompt_file`, `judge` |
| `llm_classify` | label | A judge model answers a question with one of your labels | `question`, `labels`, `include`, `prompt`/`prompt_file`, `judge` |

- **Match modes** (`mode`, `modes`, `fields`): `exact`, `ci`, `numeric[:tolerance]`, `fuzzy[:threshold]`, `regex`. `coerce: true` compares `"2"` and `2` as equal. `skip_failed: true` leaves out mock calls that raised, so a call the agent fixed and retried scores once.
- **`key` and `fields`** pair list items by one field and check the others, e.g. `key: 0, fields: {1: numeric}` for `[sku, quantity]` pairs. List scores report precision and recall as components and the missing, extra and mismatched items as details.
- **`include`** chooses what the judge sees: `input` (the case input and file names), `outcome` (how the run ended and the calls to each mock, so a missing order is stated), `output`, `expected` (the case's answer key) and `trace_summary` (tool calls, mock calls, attempts). The default is `outcome`, `output`, `expected` for `llm_judge` and `outcome`, `output` for `llm_classify`. `llm_judge` scores each criterion separately, reports each as a component (shown as success or failure with `scale: binary`) and keeps the judge's reasoning per criterion, which `report.md`, `results.csv` (`<metric>.reasoning`), `metrics.csv` and `runs/*.json` show.
- **Custom metrics:** set `type` to the dotted path of a `BaseMetric` subclass, see [Add your own metric](./metrics#add-your-own-metric).

Each metric is explained with an example in [Metrics](./metrics).

### Pass thresholds

`pass_threshold` takes `min`, `max`, `equals` and `in`, e.g. `pass_threshold: {min: 0.95}`. A bool metric without one needs `equals: true`. A run passes when it meets every `required` pass threshold; `required: false` reports a missed one as a warning. A metric with no value misses its threshold.

### Aggregates

Across runs, numbers aggregate as `mean`, bools as `rate` and labels as `distribution`; set `aggregate` to `mean`, `rate`, `sum`, `min`, `max`, `p50`, `p95` or `distribution` to change it. Each candidate also gets `pass_rate`, `first_attempt_pass_rate` and `flaky_rate`. A case is `flaky` when its repeats both passed and failed.

## Results and history

`<suite>/results/` keeps one directory per run, `latest` pointing at the newest, and a `.gitignore` so results stay out of git. `results/history.jsonl` gets one line per candidate of each run: the run, git commit, status, spend, note, prompt hash, pass rates and mean cost. `runeval --history` prints it.
