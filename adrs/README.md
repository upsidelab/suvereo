# Architectural Decision Records

One short file per architectural decision, numbered in the order they were recorded. Each record has a Status, Context, Decision and Consequences. A superseded record stays in place and links to the one that replaces it.

## Statuses

- `Proposed` — under discussion, not yet agreed.
- `Accepted` — agreed and in effect.
- `Deprecated` — no longer applies, and nothing replaces it.
- `Superseded by ADR-NNNN` — replaced by a later record, which is linked.

| ADR | Title | Status |
|-----|-------|--------|
| [0001](0001-plugin-architecture.md) | Plugin architecture and the role of suvereo-common | Accepted |
| [0002](0002-agentic-execution.md) | Agentic execution as a concept separate from conversations | Accepted |
| [0003](0003-domain-agnostic-core-and-verticals.md) | Domain-agnostic core with pluggable verticals | Accepted |
| [0004](0004-role-based-authorization.md) | Role-based authorization with global and data-set scopes | Accepted |
| [0005](0005-jwt-authentication.md) | JWT access and refresh tokens for users | Accepted |
| [0006](0006-mcp-servers-as-tool-providing-integrations.md) | MCP servers as tool-providing integrations, connected with OAuth | Accepted |
| [0007](0007-agent-self-configuration.md) | Agents declare their own configuration | Accepted |
| [0008](0008-tool-configuration-keyed-by-tool-name.md) | Tool configuration keyed by tool name | Accepted |
