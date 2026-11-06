# Conversations

A conversation suite tests an agent through chat: each case is a dialogue of several turns, in which the agent can ask questions and the user answers them. It uses the same `suite.yaml`, mocks, metrics, reports and commands as any suite.

A suite is a conversation suite when it sets `kind: conversation`, or when its agent type has no agentic execution. Any agent in `AVAILABLE_AGENTS` can run as one. The tutorial's nutrition assistant has the `weekly-meal-plan` execution, so its chat suite, `diet-vertical/evals/nutrition_chat/`, sets `kind: conversation`. It runs in a sandbox on fixture recipes, through the recipe mock from [Mocks](./mocks).

```shell
./manage.py runeval ../diet-vertical/evals/nutrition_chat/suite.yaml
```

## Who plays the user

Each case has one of two users:

- **Fixed messages** (`user_messages`): sent in order, whatever the agent answers. The conversation ends after the last one. Use them for flows you know turn by turn; they need no user model.
- **A simulated user** (`simulated_user`): an LLM given a goal, a persona and the facts it knows. It gets them as its system prompt and the conversation so far as chat messages, and on each turn writes the next message, until it says it is done, gives up, or reaches `max_turns`. Use it where the agent's questions decide the path.

```yaml
- id: dairy-free-breakfast
  description: An allergy stated up front, then the answer to the assistant's follow-up question
  user_messages:
    - I'm allergic to dairy. What could I have for breakfast?
    - No other allergies or preferences, and no calorie target.
  expected: {outcome: "Suggests only dairy-free breakfasts and mentions their calories"}

- id: peanut-free-dinner
  description: The user mentions the allergy only when asked
  simulated_user:
    goal: Get two dinner ideas that contain no peanuts, with their calories
    persona: terse, answers only what is asked
    facts: {allergies: peanuts, diet: none, daily calorie target: 1800}
    max_turns: 6
```

The nutrition assistant asks about allergies and preferences before it suggests anything. With only the first message, `dairy-free-breakfast` would end on the assistant's question, before a single recipe; the second message answers it. A simulated user answers whatever the assistant asks, from its `facts`.

| `simulated_user` field | Meaning | Default |
|---|---|---|
| `goal` | What the user wants from the conversation; the judge checks it was reached. | required, unless `class` is set |
| `persona` | How the user talks, e.g. terse, vague, chatty. | plain |
| `facts` | Everything the user knows. It answers from these and says it doesn't know anything else, so it invents no details. | none |
| `max_turns` | The turn limit; a conversation cut off here fails the run. | 10 |
| `class` | A dotted path to your own simulator, see below. | the built-in LLM user |
| `params` | Passed to your own simulator. | none |

`files` attach before the first turn, as in any case.

## suite.yaml

```yaml
name: nutrition-chat
kind: conversation                                    # chat with the agent instead of running its execution
agent: {type: nutrition-assistant}
models: [{provider: OpenAI, model: gpt-4o-mini}]
user_model: {provider: OpenAI, model: gpt-4.1-mini}   # plays the simulated users
judge: {provider: OpenAI, model: gpt-4.1-mini}        # grades the conversations
budget_usd: 0.20
reports: [report, results, transcripts]

integrations:
  - class: diet_vertical.evaluation.RecipeMockIntegration
    config: {data: {recipes: recipes.yaml}}

metrics:
  - name: searched
    type: tool_called
    params: {name: search_recipes}
    pass_threshold: {min: 1}
  - name: quality
    type: llm_judge
    params:
      criteria:
        - {name: grounded, description: "Every recipe the assistant suggests is one a search_recipes call returned"}
        - {name: safe, description: "No suggested recipe contains an allergen the user mentioned. Score 1 if the user mentioned none."}
        - {name: calories, description: "Each suggested recipe comes with its calories per serving"}
    pass_threshold: {min: 0.8}

cases: cases
```

- **`user_model`** plays every simulated user. It is set apart from `judge`; a suite with only fixed messages needs neither.
- **`judge`** grades the conversations through `llm_judge` and `llm_classify`, and decides `goal_reached` for every case with a goal.
- **`budget_usd`** counts the agent, the judge and the simulated users together.

A case can add a check of its own. `peanut-free-dinner` expects the assistant to save the allergy it learns:

```yaml
  metrics:
    - {name: saved_profile, type: tool_called, params: {name: update_user_profile}, pass_threshold: {min: 1}}
```

## What a run measures

A conversation run passes when the user finished the conversation (`conversation_completed`) and the run meets every required pass threshold. These are measured on every conversation run:

| Metric | Value | Measures |
|---|---|---|
| `conversation_completed` | bool | At least one turn, every turn answered, and the user said it was done |
| `conversation_end` | label | How it ended: `done`, `gave_up`, `max_turns`, or `error` when a turn or the run raised |
| `turns` | number | User messages sent |
| `goal_reached` | bool | Whether the simulated user reached its goal, as the judge reads the transcript; no value for a case without a goal |
| `user_cost_usd` | number | What the simulated user cost, apart from the agent's `cost_usd` and the judge's `judge_cost_usd` |

`duration_s`, `cost_usd`, the token counts, `llm_calls` and `tool_calls` are measured as in any suite. `goal_reached` is reported only; give it a `pass_threshold` to make it decide the run.

Most checks of how the agent behaved come from the judge. Its criteria read the whole dialogue: the default `include` in a conversation is `outcome`, `transcript` and `expected`, where `transcript` holds each user message and answer with what each tool called in that turn returned. A case's `expected` can be free text for the judge, as in `dairy-free-breakfast` above.

Tool and mock metrics (`tool_called`, `tool_order`, `mock_called`, `mock_calls`, `trace_event: tool_error`) count calls over the whole conversation. The output metrics (`json_subset`, `field_match`, `list_match`) read the last answer as `output.answer`, plus its fields when it is a JSON object.

The validator metrics (`attempts`, `first_attempt_success`, `failure_code`, the validator events of `trace_event`) belong to executions; `validateeval` names any a conversation suite uses.

## Reading the results

- **`report.md`** shows each candidate's pass rate, flaky rate, `goal_reached` rate and mean `turns`. Each failed conversation shows how it ended and its last two turns.
- **`transcripts/<run_id>.md`** holds each run as a readable dialogue: how it ended, the simulated user's goal, persona and facts, then every turn with the tools called. Add `transcripts` to `reports` to write it.
- **`results.csv`** has `conversation_completed`, `conversation_end`, `goal_reached`, `turns` and `user_cost_usd` per run.

## Keeping results steady

A simulated user and a judge both vary between runs. To keep a suite useful:

- Let fixed messages carry the flows that must always work, and add simulated users for the open-ended ones.
- All conversations run as one evaluation account, so a profile the assistant saves in one case is still there in the next case of the same sandbox. State in each case what it relies on, as the cases above do, rather than relying on an empty profile.
- Give each simulated user the facts it needs, so its answers stay within them. `peanut-free-dinner` gives its user the allergy, the diet and the calorie target, the three things the assistant asks about.
- Write criteria a judge can answer yes or no, and pick a judge other than the models under test.
- Set `repeats` above 1 and watch the flaky rate.

## Your own simulator

For a user with rules rather than an LLM, subclass `BaseUserSimulator` and name it in `class`:

```python
from suvereo_common.evaluation.users import BaseUserSimulator, StopReason, UserMessage


class AnswersWithTheAllergy(BaseUserSimulator):
    """Asks for a dinner, then answers every question with the allergy."""

    def next_message(self, turns):
        if len(turns) >= self.simulated_user.params.get("turns", 3):
            return UserMessage.stop(StopReason.DONE)
        return UserMessage.say("A dinner idea, please" if not turns else "I'm allergic to peanuts")
```

```yaml
- id: rule-based-user
  simulated_user:
    class: my_package.simulators.AnswersWithTheAllergy
    params: {turns: 3}
```

`next_message` gets the turns so far, each with the user's message and the agent's answer, and returns the next message or a stop (`DONE` or `GAVE_UP`). The simulator holds the case as `self.case`, its `simulated_user` settings as `self.simulated_user`, and, when the suite sets `user_model`, that model as `self.llm`: `chat(messages, system)` sends a conversation of `ChatMessage`s (from `suvereo_common.evaluation.chat_message`, each with a `role` of `user` or `assistant` and a `text`) after a system prompt and returns the model's reply, and `complete(prompt)` asks a single question.
