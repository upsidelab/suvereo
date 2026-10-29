# ADR-0001: Plugin architecture and the role of suvereo-common

## Status

Accepted

## Context

Suvereo is meant to ship with a set of pre-defined, maintained plugins, and let users choose which of them to run: the LLM model family, the integrations and the agents. Users assemble their own set-up by installing the plugins they want, without changing the core.

For that to work, the server and every plugin need to agree on the shape of the code they exchange. Without a shared definition, each plugin would depend on server internals, or the two sides would drift apart.

## Decision

Extension happens through plugins, each a standalone package (LLM providers, integrations, agents).

`suvereo-common` is the single source of truth for the interfaces between the server and the plugins. The server and every plugin import these interfaces from the package. Neither side defines them on its own.

## Consequences

- The interfaces are installed and imported from the `suvereo-common` package. The server and the plugins depend on it, so it has to be versioned and released as a package.
- Any functionality meant to be extensible, or to go into the open source, must have its interface defined in `suvereo-common`. An extension point that exists only in the server cannot be used by a plugin.
- Changing a contract in `suvereo-common` affects the server and all plugins, so it is a deliberate change.
