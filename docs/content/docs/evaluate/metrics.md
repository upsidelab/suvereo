# Metrics

A metric measures one thing about every run: a **number**, a **bool** or a **label**. Some are measured on every run with no config; the rest you add under `metrics` in `suite.yaml`, or in a case to add or replace one for that case. `./manage.py listevalmetrics` lists them all with their params.

This metric checks that the agent placed exactly one order:

```yaml
metrics:
  - name: one_order                # column name in the reports
    type: tool_called              # the built-in metric to run
    description: place_order calls # shown in the report.md legend
    params: {name: place_order}    # count calls to this tool
    pass_threshold: {equals: 1}    # a run passes with exactly one call
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

These compare the run's output, or what reached the mocks, with the case's `expected`.

### `json_subset`

The share of fields under `expected.output` that the output matches, 0–1. Fields the case leaves out are skipped, so each case names only the fields it cares about.

```yaml
# suite.yaml
- name: answer
  type: json_subset
  params:
    modes:                      # how to compare a field; any field not listed must be equal
      total: "numeric:0.01"     # a number within 0.01 of the expected one
      customer.name: ci         # the same text, ignoring upper/lower case
    coerce: true                # "ORD-1" vs ORD-1, "42.5" vs 42.5 count as equal
  pass_threshold: {min: 1}      # every expected field must match
```

```yaml
# cases/po-letter.yaml: the fields this case checks
expected:
  output:
    order_id: ORD-1
    total: 42.5
    customer: {name: acme ltd}
```

If the agent answers `{"order_id": "ORD-1", "total": "42.495", "customer": {"name": "ACME Ltd", "city": "Leeds"}, "notes": "..."}`, all three fields match: `total` is within 0.01, `customer.name` differs only in case, and `city` and `notes` are not checked. The value is 1. With `"order_id": null` it would be 2 of 3, 0.67, and the run would miss `{min: 1}`.

| Param | Meaning | Values | Default |
|---|---|---|---|
| `modes` | How to compare particular fields. Each key is a field's dotted path (`total`, `customer.name`), each value a [match mode](#match-modes). Fields left out are compared `exact`. | `exact`, `ci`, `numeric`, `numeric:<tolerance>`, `fuzzy`, `fuzzy:<threshold>`, `regex` | every field `exact` |
| `coerce` | Treat a number and its text as equal, so `"42.5"` matches `42.5`. Applies to `exact` fields. | `true`, `false` | `false` |
| `path` | Check only one part of the output. `path: customer` compares `output.customer` with `expected.output.customer`; `modes` keys are then relative to it (`name`, not `customer.name`). | a dotted path | the whole output |

- Each leaf is a field: `customer: {name: ...}` is `customer.name`; a list is one field and must match whole.
- `mismatched` in the details lists each field that missed, with `expected` and `actual`; `actual` is `null` when the output has no such field.
- `{min: 1}` needs every field, `{min: 0.5}` half of them.

### `field_match`

Whether one output field matches its expected value; bool.

```yaml
- name: status
  type: field_match
  params:
    path: status    # output.status is compared with expected.output.status
    mode: ci        # the same text, ignoring upper/lower case
```

Params: `path` in the output, `expected_path` under `expected.output` (defaults to `path`), `mode`, `coerce`.

### `list_match`

F1 of an output list against the expected one, 0–1, with precision and recall as components.

```yaml
- name: items
  type: list_match
  params:
    path: items                # the list in the output, compared with expected.output.items
    key: sku                   # an output item and an expected one are the same product when their sku is equal
    fields: {quantity: numeric} # then their quantity must be the same number
    coerce: true               # "6" and 6 count as equal
  pass_threshold: {min: 0.95}  # nearly every item right, none extra
```

`key` pairs actual items with expected ones by one field (or index, for lists such as `[sku, quantity]`), and `fields` checks the others with a match mode each. Without `key`, whole items are compared. The details list `missing`, `extra` and `mismatched` items.

**F1** is one 0–1 score for how well a list matches the expected one. It combines two questions:

- **Precision**: of the items the agent gave, how many are right? Extra or wrong items lower it.
- **Recall**: of the items expected, how many did the agent give? Missing items lower it.

F1 is their balance, 1 only when both are 1. For example, if 4 items are expected and the agent gives 3 of them plus 1 that is not expected, precision is 3/4, recall is 3/4 and F1 is 0.75. An item with the right key but a wrong field, such as the right SKU with the wrong quantity, counts as both missing and extra.

### `mock_calls`

F1 of what reached a mock against `expected.mock_calls.<method>`, 0–1. It scores what the agent sent to the outside system, whatever its output says.

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
# cases/po-letter.yaml: the order the shop should receive
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

```yaml
- name: valid
  type: json_schema
  params:
    schema_file: output.schema.json # next to suite.yaml; or schema: {...} inline
```

## How the agent worked

These read the trace: the tools the agent called, the mock calls and the validator loop.

### `tool_called`

How many times the agent called a tool; a number. `args` counts only calls with those argument values.

```yaml
- name: one_order
  type: tool_called
  params:
    name: place_order          # the tool to count
    args: {}                   # optional, e.g. {sku: MUG-RED} counts only those calls
  pass_threshold: {equals: 1}  # exactly one order
```

### `tool_not_called`

Whether the agent never called a tool; bool.

```yaml
- name: no_follow_up
  type: tool_not_called
  params:
    name: ask_user             # passes when the agent never called this tool
```

### `tool_order`

Whether the agent called tools in this order; bool. Other calls may come in between, or none with `strict: true`. A miss lists the calls in `called`.

```yaml
- name: search_first
  type: tool_order
  params:
    sequence: [search_products, place_order] # searched before ordering
    strict: false              # other calls may come in between
```

### `mock_called`

How many times a mocked method was called; a number. `args` counts only calls with those argument values.

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

These ask the suite's `judge` model, or the metric's own `judge`, about the run. `include` picks what it sees: `input`, `outcome`, `output`, `expected`, `trace_summary` and, in a conversation, `transcript`, each user message and answer with the tools called in each turn, a tool that raised marked `(raised)`. `prompt` or `prompt_file` replaces the built-in prompt; it must contain `{material}`, where the run details go. What the judge costs is reported as `judge_cost_usd`.

### `llm_judge`

Grades the run against criteria you write, 0–1. Each criterion is asked separately and reported as a component with the judge's reasoning; the value is their weighted average.

```yaml
- name: behaviour
  type: llm_judge
  params:
    include: [input, outcome, trace_summary] # what the judge sees of the run
    scale: binary              # each criterion is met (success) or not (failure)
    criteria:                  # each one is asked separately and scored on its own
      - name: adapts_search
        description: "After a search finds nothing, the next one changes approach"
      - name: explains_stop
        description: "A stop reason names each item it could not order and why"
        weight: 2              # counts twice in the average
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
| `binary` | 0 (not met) or 1 (met) | `adapts_search (failure)` / `(success)` |
| `"1-5"` | 1 (not met at all) to 5 (fully met); 4 becomes 0.75 | `adapts_search 0.75` |
| `{min: 0, max: 10}` | any number in your range; 7 becomes 0.7 | `adapts_search 0.7` |

```yaml
    scale: "1-5"               # each criterion scored 1 to 5
    samples: 3                 # wider scales vary between runs; the median of 3 steadies them
```

Binary scores are the most consistent between runs. A wider scale tells partly-met from not-met, but a judge's 3 against 4 is noisy, so pair it with `samples: 3`, which triples the judge's cost.
- Code metrics check what the agent produced; a judge suits how it worked. Write each criterion so it can be scored from what `include` shows, and say how to score the cases it does not apply to.

### `llm_classify`

Asks one question and records which of your labels the judge answered; a label. Labels aggregate as counts per candidate.

```yaml
- name: refusal_kind
  type: llm_classify
  params:
    question: Why did the agent stop?   # asked of the judge model
    labels: [unknown_item, out_of_stock, unreadable, none] # it must answer with one of these
```

## Match modes

A match mode says how an actual value is compared with the expected one. `field_match` takes one as `mode`; `json_subset` takes one per field as `modes`; `list_match` and `mock_calls` take one per item field as `fields`.

| Mode | Matches when | Expected | Matches | Doesn't match |
|---|---|---|---|---|
| `exact` | The values are equal; with `coerce: true` a number equals its text | `6` | `6` (`"6"` with `coerce`) | `6.0001`, `"six"` |
| `ci` | Case-insensitive: the text is equal, ignoring upper/lower case and extra spaces | `acme ltd` | `ACME  Ltd` | `Acme Limited` |
| `numeric` | The numbers are equal; numbers given as text count | `42.5` | `"42.5"`, `42.50` | `42.49` |
| `numeric:<tolerance>` | The numbers differ by at most the tolerance | `42.5` with `numeric:0.01` | `42.495` | `42.4` |
| `fuzzy` | The texts are at least 85% similar | `Red ceramic mug` | `Red ceramik mug` | `Blue mug` |
| `fuzzy:<threshold>` | The texts are at least this similar, 0–1 | `Green tea 100g` with `fuzzy:0.7` | `green tea 100 g` | `Black tea` |
| `regex` | The expected value, as a regular expression, matches the whole actual value | `ORD-\d+` | `ORD-1042` | `order 1042` |

Quote a mode with a colon in YAML (`"numeric:0.01"`) when it is a flow value; on its own line it works as is.

## Add your own metric

Subclass `BaseMetric` anywhere importable and set `type` to its dotted path. Declare `NAME`, `VALUE_TYPE` (`number`, `bool` or `label`) and, for params, a Pydantic model as `PARAMS`; `measure` gets the run and returns a `MetricResult`.

```python
from suvereo_common.evaluation.metrics import BaseMetric, MetricContext, MetricResult
from pydantic import BaseModel, ConfigDict


class QuantityParams(BaseModel):
    model_config = ConfigDict(extra="forbid")

    method: str = "create_order_with_items"


class TotalQuantity(BaseMetric):
    """Whether the order sent to the shop has as many units as the document, read from the case's total column."""

    NAME = "total_quantity"
    VALUE_TYPE = "bool"
    PARAMS = QuantityParams

    def measure(self, context: MetricContext) -> MetricResult:
        expected = context.case.extra.get("total")
        if expected is None:
            return MetricResult(value=None, details={"reason": "the case gives no total"})
        calls = context.trace.mock_calls_to(self.params.method)
        units = sum(int(quantity) for call in calls for _, quantity in call.arguments.get("items", []))
        matched = units == int(expected)
        return MetricResult(value=matched, details={} if matched else {"expected": expected, "actual": units})
```

```yaml
- name: units
  type: my_package.metrics.TotalQuantity # the dotted path of your class
```

- **`context`** holds the `trace` (`output`, `tool_calls`, `mock_calls`, `llm_calls`, `attempts`, `error`, and for a conversation its `turns` and `stop_reason`, with helpers such as `tool_calls_named`, `mock_calls_to` and `tool_calls_in(turn)`), the `case` (`expected` and `extra` for other CSV columns, plus `input` in an execution suite, or `user_messages` and `simulated_user` in a conversation suite), the suite's `kind` (`execution` or `conversation`), `duration_s`, `cost_usd` and the `judge` client.
- **`MetricResult`** takes the `value`, `details` that `report.md` lists under a missed threshold, and `components`, numbers that get their own `results.csv` columns; `binary_components=True` shows them as success or failure.
- **No value:** return `value=None` with a `reason` when the case gives nothing to measure. An exception is caught and recorded as the metric's `error`; the other metrics still run.
- **Params** are validated when the suite loads, so `validateeval` reports a typo before any run. A relative path in params resolves against the suite directory through the validation context key `base_dir`.
- **Matching:** `ValueMatcher`, `ListScorer` and `DottedPath` from `suvereo_common.evaluation.metrics.matching` give your metric the match modes and list scoring the built-ins use.
