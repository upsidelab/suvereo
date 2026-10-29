# ADR-0003: Domain-agnostic core with pluggable verticals

## Status

Accepted

## Context

Enthusiast was originally deeply coupled to the e-commerce domain. The database models and migrations were defined directly in the server codebase, and the e-commerce interfaces lived in `suvereo-common`.

Any other use of Enthusiast had to be forced into the e-commerce schema, and the coupling discouraged other domains from being introduced at all.

The basics we had built were not e-commerce specific: agent onboarding, configuration and tooling scaffolding, agentic executions and integrations. They could be reused in practically any domain, and agents for other domains could be built on top of them.

## Decision

Core is decoupled from the e-commerce domain. It is domain-agnostic, defines no domain entities of its own, and runs standalone.

A domain is added through a **vertical**: a domain-specific extension installed into core, enabled through `INSTALLED_VERTICALS`. A vertical defines what is specific to its domain:

- the entities: models and migrations, registered in core and persisted in the database;
- how they are handled, such as entity retrievers that agent tools use, and agent builders;
- integration types for the domain.

Agents for a domain are built on top of its vertical and depend on it. They can be separate plugins or live in the vertical's own codebase.

The e-commerce domain became the first vertical.

## Consequences

- A domain with any data shape can be built into Suvereo, without fitting it into someone else's schema.
- Core and `suvereo-common` must not contain domain entities or domain-specific interfaces. Domain code belongs in a vertical.
- Agents and tools that depend on domain entities are tied to the vertical that defines them. They are not usable on a core-only set-up.
- A set-up is composed of core, an optional vertical, and the plugins on top of them (see [ADR-0001](0001-plugin-architecture.md)). Core remains valid with no vertical configured.
