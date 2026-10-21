---
sidebar_position: 2
---

# Agent Classes

An agent is a Python class. `BaseAgent`, from `enthusiast-common`, is the contract every agent class fulfils, and AgentCore provides one implementation of it, `BaseToolCallingAgent`, which is the recommended starting point. An agent class can be defined anywhere, for example in a [plugin](/docs/concepts#plugin), in a vertical or in the AgentCore codebase itself. Wherever it lives, it is registered in `AVAILABLE_AGENTS` and used to create [agents](/docs/concepts#agent) in the UI.

## The BaseAgent contract

Every agent consists of:

- **Language model**: the model used for reasoning and text generation
- **Tools**: the [tools](/docs/concepts#tool) the agent can call
- **System prompt**: the instructions the agent follows
- **Injector**: access to repositories, chat history and memory, see [Injector](/docs/agents/injector)
- **Callback handler** (optional): receives LLM and agent events

`BaseAgent` defines the interface. Subclasses implement `get_answer(input_text) -> str` and its async counterpart `aget_answer(input_text) -> str`.

### Class variables

A metaclass checks that every non-abstract agent class defines `AGENT_ARGS`, `PROMPT_INPUT` and `TOOLS`.

| Variable | Type | Purpose |
|---|---|---|
| `NAME` | `str` | The name shown in the UI |
| `AGENT_KEY` | `str` | Unique identifier of the agent class. Agentic execution definitions refer to it |
| `AGENT_ARGS` | `RequiredFieldsModel` | Per-agent settings that change how the agent behaves. The fields become a form section in the UI. The agent decides how to use them |
| `PROMPT_INPUT` | `RequiredFieldsModel` | Per-agent settings used as variables of the system prompt. Each field is available in the prompt as `{field_name}` |
| `TOOLS` | `list` of tool configs | Tools of the agent. The settings of each tool are stored per agent as well, see [Tools](/docs/agents/tools) |
| `FILE_UPLOAD` | `bool` | Whether people can attach files in a conversation. Defaults to `False`. `BaseToolCallingAgent` adds the file tools to `TOOLS` when it is `True` |

`AGENT_ARGS` and `PROMPT_INPUT` are both entered in the UI and stored per agent. The intended use differs: `AGENT_ARGS` is for settings that change how the agent behaves, and `PROMPT_INPUT` is for values that go into the system prompt. The framework only stores the values; the agent decides what to do with them.

Example agent declaration (inheriting from `BaseToolCallingAgent`, described in the [next section](#basetoolcallingagent)):

```python
class AgentConfiguration(RequiredFieldsModel):
    fallback_answer: str = Field(
        title="Fallback Answer", description="Returned when the agent produces an empty answer", default="Sorry, I could not find an answer."
    )

class PromptInputSchema(RequiredFieldsModel):
    output_format: str = Field(title="Output Format", description="Expected response format")

# Attached to agent via AgentConfig
SYSTEM_PROMPT = """
You answer questions about articles. Format every answer as {output_format}.
"""

class ExampleAgent(BaseToolCallingAgent):
    AGENT_KEY = "example-agent"
    NAME = "Example"
    AGENT_ARGS = AgentConfiguration
    PROMPT_INPUT = PromptInputSchema
    TOOLS = [LLMToolConfig(tool_class=ExampleTool)]

    def get_answer(self, input_text: str) -> str:
        answer = super().get_answer(input_text)
        return answer or self.AGENT_ARGS.fallback_answer
```

`SYSTEM_PROMPT` is passed to the agent through `AgentConfig.system_prompt`, see [Prompts](/docs/agents/prompts). The `{output_format}` placeholder is filled from the `output_format` field of `PROMPT_INPUT`. The agent reads `fallback_answer` from `AGENT_ARGS` and returns it when the model produces an empty answer.

By default the `PROMPT_INPUT` fields are passed to the system prompt by name, and an agent class can change which values are passed and how, see [Template Variables](/docs/agents/prompts#template-variables).

When the agent is built, the class variables `AGENT_ARGS` and `PROMPT_INPUT` are replaced with instances holding the saved values, so `self.AGENT_ARGS.fallback_answer` and `self.PROMPT_INPUT.output_format` return what was entered in the UI. 

## BaseToolCallingAgent

`BaseToolCallingAgent` implements the standard tool calling pattern, which relies on the function calling support of the language model. It is the recommended base class for new agents. It lives in the `enthusiast-agent-tool-calling` plugin.

`get_answer()` runs one turn:

1. Builds the context messages: the recent history trimmed to a token budget, preceded by the conversation summary when a memory compactor is enabled (see [Memory](/docs/agents/memory)).
2. Builds a LangGraph agent from the language model, the tools and the system prompt, and invokes it with the context and the new message.
3. Records the messages produced during the turn in the chat history, and runs the memory compactor if one is present.
4. Returns the final answer.

```python
def get_answer(self, input_text: str) -> str:
    context_messages = self._build_context_messages()
    result = self._build_agent().invoke(
        {"messages": self._build_input_messages(context_messages, input_text)},
        config=self._build_invoke_config(),
    )
    return self._record_turn(result, context_messages)
```

`aget_answer()` is the async equivalent. It lets tools supplied by integrations, such as MCP servers, be awaited.