# Suites and Cases

A suite is a directory with a `suite.yaml` and its cases. `suite.yaml` holds what every case shares: the agent, the models to compare, the mocks and the metrics. Each case holds what is specific to one test: the documents the agent gets and the right result for them.

```text
evals/order_intake/
├── suite.yaml          # the agent, models, mocks, metrics
├── data/products.yaml  # mock data the suite points at
├── prompts/v2.txt      # a prompt variant to compare
└── cases/
    ├── po-letter.yaml  # one case: its files and expected result
    ├── po-letter.pdf
    └── ...
```

`./manage.py validateeval <suite.yaml>` checks a suite for free and prints the runs it would make; `./manage.py evalschema` prints the JSON Schema of `suite.yaml` for editor completion.

## suite.yaml

The order-intake suite, every line explained:

```yaml
name: order-intake                     # shown in reports; defaults to the directory name
description: Purchase orders as PDFs and photos

agent: {type: enthusiast-agent-order-intake}   # the agent type, run in a throwaway DataSet

models:                                # the models to run the agent with
  - {provider: OpenAI, model: gpt-4o-mini}
variants:                              # prompts to compare with the agent's own
  - {name: v2, system_prompt_file: prompts/v2.txt}
judge: {provider: OpenAI, model: gpt-4.1-mini}  # the model llm_judge asks

repeats: 1                             # runs per case, model and variant
budget_usd: 0.10                       # stop when this much has been spent
min_pass_rate: 0.8                     # each candidate must pass 80% of its runs
reports: [report, results, comparison, cases]

integrations:                          # mocks for every system the agent reaches
  - class: enthusiast_vertical_common.evaluation.ECommerceMockIntegration
    config: {data: {catalog: data/products.yaml}}

metrics:                               # what each run is measured on
  - name: line_items
    type: mock_calls
    params: {method: create_order_with_items, arg: items, key: 0, fields: {1: numeric}, coerce: true}
    pass_threshold: {min: 0.95}
  - name: order_id
    type: json_subset                  # the answer has the expected fields
    pass_threshold: {min: 1}

cases: cases                           # a directory of case files
```

Only `agent`, `metrics` and `cases` are required.

### `agent`

Which agent to test. Set one of:

| Form | Runs |
|---|---|
| `{type: <agent key>}` | A new agent of that type in a throwaway DataSet. The mocks' data, such as the catalog, is synced into it, and it is removed after the run (`--keep-run-data` keeps it). |
| `{type: <agent key>, config: {...}}` | The same, with this agent config. |
| `{id: <agent id>}` | An agent you already configured in the UI, with its DataSet and catalog as they are. The suite's mocks replace its integrations; one the suite leaves unmocked runs for real only with `--allow-real-integrations`. |

The agent type must be in `AVAILABLE_AGENTS` and its execution in `AVAILABLE_AGENTIC_EXECUTION_DEFINITIONS`. `execution_key` picks the execution when the agent type has more than one.

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

### `judge`

The model `llm_judge` and `llm_classify` ask, `{provider, model}` like a model. Pick one other than the models under test, as a model favours its own answers. A metric can name its own with `params.judge`. The judge's cost is reported as `judge_cost_usd`, apart from the agent's.

### Run size and limits

| Field | Meaning | Default |
|---|---|---|
| `repeats` | Runs per case, model and variant. Above 1, cases whose repeats disagree show as flaky. | 1 |
| `budget_usd` | The run stops once this much is spent, agent and judge together, and is marked partial (exit code 3). `--budget` overrides it. | no limit |
| `min_pass_rate` | The share of runs each candidate must pass, 0–1. With it, `report.md` opens with a verdict and a candidate below it makes the run exit 1. Without it the run only reports. | none |

A run passes when it meets every required pass threshold of its metrics, see [Metrics](./metrics).

### `reports`

What to write to `results/<date>-<id>/` besides `summary.json`, which is always written: `report`, `results`, `comparison`, `cases`, `metrics`, `traces` and, for a conversation suite, `transcripts`. The default is `report` and `results`; `--reports` overrides it. [Getting started](./getting-started#2-read-the-results) says what each holds.

### `integrations`

The mocks standing in for every system the agent reaches, each with `class` (a mock integration) or `interface` (a mock built from YAML alone), and a `config` with the mock's `data` and per-method `behaviour`. Paths in `data` are relative to the suite. See [Mocks](./mocks).

### `metrics`

What every run is measured on, each with a `type`, a `name`, `params` and an optional `pass_threshold`. See [Metrics](./metrics).

### `cases`

Where the cases are, relative to the suite:

| Form | Reads |
|---|---|
| `cases: cases` | Every `.yaml`, `.yml` and `.csv` file directly in that directory, in name order. |
| `cases: cases.csv` | One file. |
| `cases: [cases.csv, extra/]` | Several files and directories. |
| `cases: [{id: smoke, files: [po.pdf], expected: {...}}]` | Cases written inline in the suite. |

Case ids must be unique across the suite. `--case <id>` and `--tag <tag>` run a few of them.

## A case

A YAML case file holds one case, or a list of them:

```yaml
id: po-letter                          # unique; names the case in reports and for --case
description: A free-text letter with spelled-out quantities   # shown with its failed runs
tags: [basic]                          # groups cases; --tag basic runs them
files: [po-letter.pdf]                 # what the agent gets, relative to this file
expected:                              # the right result, read by the metrics
  mock_calls:
    create_order_with_items:           # the shop should get exactly this order
      - items: [[MUG-RED, 6], [TEA-GRN, 2], [SPN-STL, 12], [KTL-ELC, 1]]
  output: {order_id: ORD-1}            # and the agent's answer should contain this
```

| Field | Meaning |
|---|---|
| `id` | Unique across the suite. |
| `description`, `tags` | Shown with the case's failed runs; tags also select cases with `--tag`. |
| `files` | Attached to the conversation, relative to the case file: PDFs and images (`.png`, `.jpg`). |
| `input` | The execution's other input fields, if the agent takes any, checked against its input type. |
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

A case with nothing at a metric's path gives that metric no value, which misses its pass threshold. Replace the metric on that case without a threshold to only report it.

### Changing a mock or a metric for one case

A case that needs the shop to fail, and checks it differently:

```yaml
id: po-out-of-stock
description: The shop rejects the order; the run must fail cleanly
tags: [error-path]
files: [po-out-of-stock.pdf]
integrations:                          # same class as in the suite, so this changes that mock
  - class: enthusiast_vertical_common.evaluation.ECommerceMockIntegration
    config:
      behaviour:
        create_order_with_items:       # this method now raises; others behave as in the suite
          raises: {error: ECommerceConnectorError, message: "Out of stock: KTL-ELC"}
expected:
  failure_code: validation_failed
  mock_calls: {create_order_with_items: [{items: [[KTL-ELC, 40], [MUG-RED, 2]]}]}
metrics:
  - {type: json_subset, name: order_id}  # same name as the suite's, no threshold: only reported here
```

- **`integrations`** apply to the suite's mock with the same `class` or `interface`. `config` is merged into the suite's, and a method's `behaviour` replaces the suite's for that method.
- **`metrics`** replace the suite's metric with the same `name`, or are added when the name is new.

## Cases in a CSV

Simple cases fit one row each, which suits many similar documents:

```csv
id,description,tags,files,expected.mock_calls.create_order_with_items.0.items,expected.output.order_id
po-skus,SKUs only,basic,po-skus.pdf,"[[""KTL-ELC"",2],[""SUG-CUB"",10]]",ORD-1
po-photo,A phone photo,basic;image,po-photo.jpg,"[[""MUG-RED"",6]]",ORD-1
```

- `id`, `description`, `tags` and `files` are columns; separate several tags or files with `;`, or write them as a JSON list.
- `input.<field>` and `expected.<dotted.path>` columns build those mappings; a number in the path indexes a list, so `create_order_with_items.0.items` is the first call's items.
- A cell starting with `[`, `{` or `"` is read as JSON; anything else stays text.
- Any other column reaches custom metrics as `case.extra`.

A case needing its own mocks or metrics goes in a YAML file; YAML and CSV cases can sit in the same directory.
