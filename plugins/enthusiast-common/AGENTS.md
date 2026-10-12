# enthusiast-common

The contracts every plugin builds against. It is published to PyPI and versioned independently of the server (`pyproject.toml`); the server pins an exact version, so a contract change needs a version bump and a matching pin in `server/pyproject.toml`.

Public interfaces here carry docstrings (purpose, parameters, return values). Python code conventions are in `server/AGENTS.md` ("Code conventions"); they apply here too.

## Contents (`enthusiast_common/`)

- `agents/`, `builder/`, `injectors/` — `BaseAgent`, agent builder, dependency injection of retrievers, connectors and memory
- `registry/` — base registries for agents, language models and embedding providers
- `tools/` — `BaseTool`, `BaseFunctionTool`, `BaseLLMTool`, `BaseAgentTool`
- `repositories/`, `entities/` — repository bases and entity contracts for data access
- `retrievers/`, `indexing/` — retrieval and vector-store contracts, indexing pipeline contracts
- `integrations/`, `oauth/` — integration plugin bases and OAuth helpers
- `agentic_execution/` — contracts for agentic executions (input, result, status, memory)
- `llm/`, `memory/`, `services/`, `callbacks/`, `config/`, `structures/` — LLM, memory and service contracts, Pydantic config models, content structures

## Tests

Tests live in `tests/`; run them with `pytest` from the server's environment (`cd server && poetry run pytest ../plugins/enthusiast-common/tests`).
