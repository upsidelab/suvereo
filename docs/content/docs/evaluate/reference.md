---
sidebar_position: 3
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
| `0` | Every candidate reached `pass_threshold`. |
| `1` | At least one candidate is below `pass_threshold`. |
| `2` | The suite or an option is invalid. |
| `3` | The run stopped early, at the budget or at a call it had no price for; it is marked partial. |
| `4` | The run crashed. |

## Suite

Only `agent`, `metrics` and `cases` are required.

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
| `pass_threshold` | Minimum pass rate per candidate (default 0.8). |
| `metrics` | Measured on every case. |
| `reports` | Any of `report`, `results`, `comparison`, `cases`, `metrics`, `traces` (default `report`, `results`). `summary.json` is always written. |
| `cases` | A case file, a directory of them, inline cases, or a list of these. |

A **candidate** is one model and variant, shown as `<model label>/<variant>`. A model's `pricing` (`input_per_million`, `output_per_million`, `cached_input_per_million`) overrides the bundled price table for that model.

## Cases

| Field | Meaning |
|---|---|
| `id` | Unique across the suite. |
| `description`, `tags` | Tags select cases with `--tag` and get their own rows in the report. |
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

Every metric config takes `type`, `name` (defaults to the type; required to use a type twice), `params`, `gate`, `required` and `aggregate`.

**Measured on every run:** `execution_succeeded`, `failure_code`, `attempts`, `first_attempt_success`, `duration_s`, `cost_usd`, `input_tokens`, `output_tokens`, `llm_calls`, `tool_calls`.

| Type | Value | Params |
|---|---|---|
| `field_match` | bool | `path`, `expected_path`, `mode`, `coerce` |
| `json_subset` | share of expected fields matched | `path`, `modes` per field, `coerce` |
| `list_match` | F1 of a list | `path`, `expected_path`, `key`, `fields`, `coerce` |
| `mock_calls` | F1 of a mock argument over its calls | `method`, `arg`, `key`, `fields`, `coerce` |
| `json_schema` | bool | `schema` or `schema_file` |
| `tool_called` | count | `name`, `args` |
| `tool_not_called` | bool | `name` |
| `tool_order` | bool | `sequence`, `strict` |
| `mock_called` | count | `method`, `args` |
| `trace_event` | bool | `event`: `retry`, `tool_error`, `validator_failed[:code]` or `stop_execution` |
| `llm_judge` | 0–1 | `criteria` (`name`, `description`, `weight`), `scale` (`binary`, `1-5` or `{min, max}`), `include`, `samples`, `prompt`/`prompt_file`, `judge` |
| `llm_classify` | label | `question`, `labels`, `include`, `prompt`/`prompt_file`, `judge` |

- **Match modes** (`mode`, `modes`, `fields`): `exact`, `ci`, `numeric[:tolerance]`, `fuzzy[:threshold]`, `regex`. `coerce: true` compares `"2"` and `2` as equal.
- **`key` and `fields`** pair list items by one field and check the others, e.g. `key: 0, fields: {1: numeric}` for `[sku, quantity]` pairs. List scores report precision and recall as components and the missing, extra and mismatched items as details.
- **`include`** chooses what the judge sees: `output`, `expected`, `input_text`, `trace_summary`. `llm_judge` scores each criterion separately and reports each as a component.
- **Custom metrics:** set `type` to the dotted path of a `BaseMetric` subclass.

### Gates

`gate` takes `min`, `max`, `equals` and `in`. A bool metric without a gate is gated on `equals: true`. A run passes when every `required` gate passes; `required: false` reports a failed gate as a warning. A metric with no value fails its gate.

### Aggregates

Across runs, numbers aggregate as `mean`, bools as `rate` and labels as `distribution`; set `aggregate` to `mean`, `rate`, `sum`, `min`, `max`, `p50`, `p95` or `distribution` to change it. Each candidate also gets `pass_rate`, `first_attempt_pass_rate` and `flaky_rate`, overall and per tag. A case is `flaky` when its repeats both passed and failed.

## Results and history

`<suite>/results/` keeps one directory per run, `latest` pointing at the newest, and a `.gitignore` so results stay out of git. `results/history.jsonl` gets one line per candidate of each run: the run, git commit, status, spend, note, prompt hash, pass rates and mean cost. `runeval --history` prints it.
