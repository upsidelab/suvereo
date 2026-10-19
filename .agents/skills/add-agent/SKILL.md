---
name: add-agent
description: Scaffold a new Enthusiast agent (tool-calling agent package, config provider, tools, prompt, optional agentic execution) and register it in settings. Use when asked to add, create or build a new agent.
---

# Add an agent

An agent is a Python package that the server discovers through `AVAILABLE_AGENTS` in `server/pecl/settings_override.py`. It depends on `enthusiast-common` and `enthusiast-agent-tool-calling`, never on the server.

There are two ways to ship it:
- **Standalone plugin** — its own installable package (own `pyproject.toml`, `src/` layout). Recommended for agents maintained by the Enthusiast team.
- **In the codebase** — a plain package living directly in a codebase that is already importable by the server (e.g. a vertical's own code). No packaging, no install step.

Sections marked *(standalone plugin only)* are skipped for in-codebase agents. Everything else applies to both.

Where to look in this repo:
- Contracts: `plugins/enthusiast-common/` (`BaseAgent`, `BaseAgentConfigProvider`, tools, config models, agentic execution) — read its `AGENTS.md`.
- Base agent to subclass: `plugins/enthusiast-agent-tool-calling/` (also the reference for the package layout and `pyproject.toml`).
- Registry that loads agents: `server/agent/core/registries/agents/agent_registry.py`.

## 1. Settle the design first

Ask only what the code cannot tell you:
- Agent name and purpose (drives `AGENT_KEY`, `NAME`, the prompt).
- Which tools it needs. Reuse existing tools (e.g. from `plugins/enthusiast-agent-tools`, or a vertical's tools) before writing new ones.
- Does it need a vertical's retrievers (e.g. `injector.<entity>_retriever`)? If yes it needs the vertical's builder as `BUILDER_CLASS`; if no, leave `BUILDER_CLASS` unset so the framework's default `AgentBuilder` is used.
- Conversation only, or also an agentic execution (autonomous, API-triggered batch run)?
- Does it accept file uploads (`FILE_UPLOAD = True` adds the default file tools)?
- Where it lives: a standalone plugin (under `plugins/` for domain-agnostic agents), or directly in a codebase (which one, and which package inside it).

## 2. Layout

The agent package has the same contents in both cases:

```
<package>/
  __init__.py       # exports the agent and the config provider
  agent.py
  config.py
  prompt.py
  tools/            # only if the agent has its own tools
    __init__.py
    <thing>_tool.py
```

- **In the codebase:** `<package>` is a directory inside the target codebase, named `<name>_agent` (or following that codebase's naming). The dotted path used for registration is `<its import path>.<Name>Agent`. Stop here; do not add the packaging files below.
- **Standalone plugin:** wrap it with the packaging files and use `src/enthusiast_agent_<name>/` as `<package>`:

```
enthusiast-agent-<name>/
  pyproject.toml
  README.md
  src/enthusiast_agent_<name>/   # the package above
```

### Packaging *(standalone plugin only)*

`pyproject.toml`: Poetry with a `src` layout, modelled on `plugins/enthusiast-agent-tool-calling/pyproject.toml`. Dependencies: `enthusiast-common`, `enthusiast-agent-tool-calling`, `langchain`, plus the vertical package if you use its builder or retrievers. Take version ranges from that file and from the current `enthusiast-common` version, not from memory.

```toml
[tool.poetry]
packages = [{include = "enthusiast_agent_<name>", from = "src"}]
```

## 3. Agent class (`agent.py`)

Subclass `BaseToolCallingAgent` and only declare data:

```python
from enthusiast_agent_tool_calling import BaseToolCallingAgent
from enthusiast_common.config.base import LLMToolConfig

from .tools import <Thing>Tool


class <Name>Agent(BaseToolCallingAgent):
    AGENT_KEY = "enthusiast-agent-<name>"
    NAME = "<Human Name>"
    TOOLS = [LLMToolConfig(tool_class=<Thing>Tool)]
    FILE_UPLOAD = False
```

- `AGENT_KEY` is stored on agents in the database: unique, and never changed after release.
- Tool config types come from `enthusiast_common.config`: `FunctionToolConfig`, `LLMToolConfig` (the tool gets an LLM), `AgentToolConfig`, `FileToolConfig`.

## 4. Config provider (`config.py`)

```python
from enthusiast_common.agents import BaseAgentConfigProvider, ConfigType
from enthusiast_common.config import AgentConfigWithDefaults

from .agent import <Name>Agent
from .prompt import <NAME>_AGENT_PROMPT


class <Name>ConfigProvider(BaseAgentConfigProvider):
    def get_config(self, config_type: ConfigType = ConfigType.CONVERSATION) -> AgentConfigWithDefaults:
        return AgentConfigWithDefaults(
            system_prompt=<NAME>_AGENT_PROMPT,
            agent_class=<Name>Agent,
            tools=<Name>Agent.TOOLS,
        )
```

Everything else (LLM, repositories, memory, registries) comes from the server's defaults.

- Set `BUILDER_CLASS = <Vertical>AgentBuilder` on the provider only when a vertical builder is needed.
- Branch on `config_type` only when the agent supports agentic execution: `ConfigType.CONVERSATION` vs `ConfigType.AGENTIC_EXECUTION_DEFINITION` (typically a different prompt and an extra tool that stops the run).

The registry finds the provider by importing the module path of the agent (the dotted path minus the class name) and looking for a `BaseAgentConfigProvider` subclass in it, so `__init__.py` must export the provider next to the agent:

```python
from .agent import <Name>Agent
from .config import <Name>ConfigProvider

__all__ = ["<Name>Agent", "<Name>ConfigProvider"]
```

## 5. Tools (`tools/`)

Subclass one of the base tools from `enthusiast_common.tools`, matching what the tool needs injected:

| Base class | Constructor receives | Config type | Description |
| --- | --- | --- | --- |
| `BaseFunctionTool` | nothing | `FunctionToolConfig` | The simplest tool, needing no connection to Enthusiast internals (those are provided via the injector). |
| `BaseLLMTool` | `data_set_id`, `llm`, `injector` | `LLMToolConfig` | A tool with access to the LLM and the injector. |
| `BaseFileTool` | `data_set_id`, `conversation_id`, `llm`, `injector`, `llm_registry` | `FileToolConfig` | Like an LLM tool, but dedicated to accessing uploaded files only. |
| `BaseAgentTool` | `agent` | `AgentToolConfig` | A tool which is itself an agent. |

Only `BaseLLMTool` and `BaseFileTool` have `self._injector`. A metaclass checks the required class attributes at import time: `NAME`, `DESCRIPTION`, `ARGS_SCHEMA`, `RETURN_DIRECT`.

```python
from enthusiast_common.tools import BaseLLMTool
from pydantic import BaseModel, Field


class <Thing>ToolInput(BaseModel):
    query: str = Field(description="What to look for.")


class <Thing>Tool(BaseLLMTool):
    NAME = "<thing>"
    DESCRIPTION = "Use it to <when and why the model should call this>."
    ARGS_SCHEMA = <Thing>ToolInput
    RETURN_DIRECT = False

    def run(self, query: str) -> str:
        retriever = self._injector.<entity>_retriever
        ...
```

LLM and file tools reach retrievers, connectors and memory through `self._injector`; a tool that needs them must subclass one of those two. `DESCRIPTION` and every field description are read by the LLM: write them for the model and say when to use the tool. Export tools from `tools/__init__.py`.

## 6. Prompt (`prompt.py`)

A module-level string constant: the agent's job, when to use each tool, the required output format.

## 7. Agentic execution (optional)

Add `execution_input.py` and `execution_definition.py`:

```python
from enthusiast_common.agentic_execution import (
    BaseAgenticExecutionDefinition,
    ExecutionConversationInterface,
    ExecutionInputType,
    IsValidJsonValidator,
    StopExecutionValidator,
)


class <Name>AgenticExecutionInput(ExecutionInputType):
    additional_instructions: str | None = None


class <Name>AgenticExecutionDefinition(BaseAgenticExecutionDefinition):
    EXECUTION_KEY = "<name>"
    AGENT_KEY = "enthusiast-agent-<name>"
    NAME = "<Human Name>"
    INPUT_TYPE = <Name>AgenticExecutionInput
    VALIDATORS = [StopExecutionValidator, IsValidJsonValidator]

    def execute(self, input_data: <Name>AgenticExecutionInput, conversation: ExecutionConversationInterface) -> str:
        return conversation.ask(input_data.additional_instructions or "<default task>")
```

`AGENT_KEY` must equal the agent's. Export the definition from `__init__.py` and register it in `AVAILABLE_AGENTIC_EXECUTION_DEFINITIONS`. Contracts: `plugins/enthusiast-common/enthusiast_common/agentic_execution/`.

## 8. Register

In `server/pecl/settings_override.py` add the dotted path of the agent class to `AVAILABLE_AGENTS`:
- standalone plugin: `"enthusiast_agent_<name>.<Name>Agent"`;
- in the codebase: `"<import path of the package>.<Name>Agent"`.

*(standalone plugin only)* Install the package into the server's environment (`pip install -e <dir>` or a path dependency). In-codebase agents need no install.

The agent then becomes selectable for data sets in the UI.

## 9. Tests and checks

- Test non-trivial tool logic next to the package (`tests/`, or the host codebase's own test location), mocking the LLM and the injector. Registry behaviour is already covered in `server/agent/tests/`.
- Run `ruff check` and `ruff format` on the new code.
- No docstrings or comments on implementations (see "Code conventions" in `server/AGENTS.md`); docstrings belong to `enthusiast-common` contracts.
- If the change adds a top-level directory (a standalone plugin does), update the relevant `AGENTS.md`.
