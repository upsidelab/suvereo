# Evaluate an Agent

An evaluation suite runs your agent on a set of cases, measures every run and writes reports you can compare across models, prompts and code changes. Suites run against real LLMs with mocked integrations, so a run places no real orders and costs a few cents.

## Before you start

Run the commands from `server/`. The agent type under test must be registered in your settings; for order intake that means both lists:

```python
AVAILABLE_AGENTS = [..., "enthusiast_agent_order_intake.OrderIntakeAgent"]
AVAILABLE_AGENTIC_EXECUTION_DEFINITIONS = [..., "enthusiast_agent_order_intake.OrderIntakeAgenticExecutionDefinition"]
```

The suites below ship with the order-intake agent in the [Enthusiast repository](https://github.com/upsidelab/enthusiast). The commands assume it is cloned next to this repository. The suites call OpenAI, so set `OPENAI_API_KEY`.

## 1. Run the quickstart

The quickstart suite ships with the order-intake agent: three purchase orders, a 10-product catalog and a mocked shop.

```shell
./manage.py validateeval ../../enthusiast/plugins/enthusiast-agent-order-intake/evals/quickstart/suite.yaml
./manage.py runeval ../../enthusiast/plugins/enthusiast-agent-order-intake/evals/quickstart/suite.yaml
```

`validateeval` is free: it checks the suite and prints how many runs it plans. `runeval` builds a throwaway DataSet, syncs the catalog into it, runs each case and removes the DataSet afterwards. It costs under a cent and stops at the suite's `budget_usd`.

## 2. Read the results

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

## 3. Run the order-intake suite

`evals/order_intake/` is the realistic baseline: PDF and photographed orders, two-page orders, and orders the agent must refuse, on gpt-4o-mini with two prompts.

```shell
./manage.py runeval ../../enthusiast/plugins/enthusiast-agent-order-intake/evals/order_intake/suite.yaml --parallel 4
```

The comparison table puts `gpt-4o-mini/default` and `gpt-4o-mini/v2` side by side; compare another model with `--model gpt-4o-mini --model OpenAI:gpt-4.1-nano`. Narrow a run while you work:

```shell
./manage.py runeval suite.yaml --model gpt-4o-mini --tag image          # one model, the image cases
./manage.py runeval suite.yaml --case po-letter --repeats 3              # one case, three times
./manage.py runeval suite.yaml --rerun-failed latest --baseline latest   # only what failed last time
./manage.py runeval suite.yaml --prompt-file my-prompt.txt               # try a prompt without editing the suite
./manage.py runeval suite.yaml --history                                 # every run so far, one line each
```

With `--baseline`, `report.md` gains a **Baseline diff**: each candidate's pass rate and metrics before → after, and the cases that regressed or improved. Add `--note "<what you changed>"` to label a run in the history.

## 4. Make a suite for your own agent

Copy `quickstart/` next to your agent and change three things in `suite.yaml`; [Suites and Cases](./suites) explains every field:

- `agent.type`: your agent's key;
- `integrations`: the mocks your agent needs, see [Mocks](./mocks);
- `metrics`: what a good run looks like for your agent.

```yaml
agent: {type: my-agent}
models: [{provider: OpenAI, model: gpt-4o-mini}]
budget_usd: 0.10
integrations:
  - class: enthusiast_vertical_common.evaluation.ECommerceMockIntegration
    config: {data: {catalog: catalog.yaml}}
metrics:
  - {type: tool_called, name: one_order, params: {name: place_order}, pass_threshold: {equals: 1}}
cases: cases.csv
```

To run an agent you already configured in the UI, use `agent: {id: <agent id>}`; its DataSet and catalog are used as they are, and the suite's mocks replace its integrations. An integration the suite leaves unmocked runs for real only with `--allow-real-integrations`.

## 5. Add a case

Simple cases are rows in `cases.csv`. `files` are relative to the CSV, and a cell starting with `[`, `{` or `"` is read as JSON:

```csv
id,description,files,expected.mock_calls.create_order_with_items.0.items
po-skus,SKUs only,po-skus.pdf,"[[""KTL-ELC"",2],[""SUG-CUB"",10]]"
```

A case that needs its own mock behaviour or metrics goes in a YAML file; put it in a `cases/` directory and set `cases: cases`:

```yaml
id: po-out-of-stock
description: The shop rejects the order; the run must fail cleanly
tags: [error-path]
files: [po-out-of-stock.pdf]
integrations:
  - class: enthusiast_vertical_common.evaluation.ECommerceMockIntegration
    config: {behaviour: {create_order_with_items: {raises: {error: ECommerceConnectorError, message: "Out of stock"}}}}
expected:
  failure_code: validation_failed
```

`expected.failure_code` marks a case that should fail: the run passes when the execution fails with that code.

## 6. Add a metric

[Metrics](./metrics) explains each built-in metric and how to write your own; `./manage.py listevalmetrics` lists them. A metric with a `pass_threshold` decides whether a run passes; one without is measured and reported only.

```yaml
metrics:
  - name: line_items
    type: mock_calls
    params: {method: create_order_with_items, arg: items, key: 0, fields: {1: numeric}, coerce: true}
    pass_threshold: {min: 0.95}
  - name: behaviour
    type: llm_judge
    params:
      include: [input, outcome, trace_summary]
      criteria:
        - name: adapts_search
          description: "After a search finds nothing, the next one changes approach instead of repeating it"
```

Code metrics check what the agent produced; a judge reads the trace and grades how it worked. `llm_judge` needs a `judge` model in the suite. Pick one other than the models under test, as a model favours its own answers. The judge explains each score; read its reasoning under each failed run in `report.md`, in the `behaviour.reasoning` column of `results.csv`, or in `runs/*.json`.

## 7. Add a mock

Anything your agent reaches outside Suvereo goes through an integration, and a suite replaces each one with a mock. [Mocks](./mocks) covers the three ways to build one, from a few lines of YAML to a mock integration your vertical ships.

For every option, field and metric, see the [Reference](./reference).
