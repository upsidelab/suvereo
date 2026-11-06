# Using the Suvereo Starter

The [Suvereo starter](https://github.com/upsidelab/suvereo-starter) is a repository to build on. It runs the Suvereo server and frontend with Docker Compose and has a place for your own code: [domain definitions](/docs/concepts#domain-definition), [agents](/docs/concepts#agent), [integrations](/docs/concepts#integration) and anything else you want to wire into Suvereo. To run it, follow [Installation](/docs/getting-started/installation).

## What is included

The starter ships with a diet advice domain definition (`server/src/diet_advice_domain/`) as a working example: models and migrations, recipe and user sources, a nutrition agent and a weekly meal plan [agentic execution](/docs/concepts#agentic-execution). It is the same domain the [tutorial](/docs/customization/tutorial) builds, so the two can be read side by side. You can keep it, change it or remove it.

## Layout

```
server/    Dockerfile, config/ (sample.env, settings_override.py), src/ (your code and pyproject.toml)
frontend/  config/sample.env (copy to config/.env)
```

## Your code

`server/src/` is part of the repository, so it is yours to change. Define your own domain definitions (entities and migrations), agents, agentic executions and integrations there, then register them in `server/config/settings_override.py`:

- `INSTALLED_DOMAIN_DEFINITIONS`
- `AVAILABLE_AGENTS`
- `AVAILABLE_AGENTIC_EXECUTION_DEFINITIONS`
- `CATALOG_INTEGRATION_PLUGINS` and `CATALOG_INTEGRATION_MANAGERS`

See [Domain definitions](/docs/customization/domain-definitions) and [Integrations](/docs/customization/integrations) for what each part contains.

## Packages from PyPI

`server/src/pyproject.toml` describes your code as a Python package. Domain definitions, agents and integrations published by others can be added to its dependencies, and they are installed into the image together with your code. Register them in `settings_override.py` the same way as your own.

## How the image is built

`server/Dockerfile` starts from the Suvereo server image, builds `server/src/` into a wheel and installs it with its dependencies, then replaces `pecl/settings_override.py` with `server/config/settings_override.py`. The frontend runs from the Suvereo frontend image, configured through `frontend/config/.env`.

## Testing against unreleased Suvereo images

To try the starter against a local checkout of Suvereo, build the development images from the Suvereo repository root:

```shell
docker build -f server/Dockerfile.development -t suvereo-server:dev .
docker build -t suvereo-frontend:dev frontend/
```

Then, in the starter:

```shell
export SUVEREO_VERSION=dev
docker compose build && docker compose up
```
