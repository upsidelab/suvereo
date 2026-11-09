# Tutorial: Building a Domain Definition

This tutorial builds a [domain definition](/docs/concepts#domain-definition) from an empty directory to a working feature. By the end, an instance of Suvereo knows about recipes and the people who eat them, a user can ask an [agent](/docs/concepts#agent) for meals that suit them, and an API call can return a validated meal plan for a week.

The example is a domain definition for personalised nutrition, the **diet domain definition**. It is one example of how a [domain](/docs/concepts#domain) can be described. The parts are the same for any other domain, so you can follow the tutorial as written and then replace recipes and diets with the data and systems of your own.

## What you will build

- **Data.** Two [entities](/docs/concepts#entity): `Recipe`, which is searchable by meaning, and `UserProfile`, which holds a person's allergies, dietary preferences and daily calorie target.
- **Integration types.** A recipe source and a user source: the kinds of external systems the domain definition can import from.
- **Integrations.** A sample of each, which bring recipes and users into a [data set](/docs/concepts#data-set), and one that connects a real recipe API.
- **An agent.** A nutrition assistant that finds recipes for a user in a [conversation](/docs/concepts#conversation), using tools that search the recipes and read and update the user's profile.
- **An agentic execution.** A weekly meal plan that runs in the background, started through the API, and is checked against the user's allergies and calorie target before it is returned.

## Pages

Each page builds on the previous one and leaves the instance in a working state.

| Page | Adds | Explained in |
|---|---|---|
| [The domain definition](/docs/customization/tutorial/domain-definition) | Entities, the recipe retriever, the profile accessor, the injector and builder, registration and migrations | [Domain definitions](/docs/customization/domain-definitions) |
| [The integrations](/docs/customization/tutorial/integrations) | The recipe and user source types, their managers and two sample integrations | [Integrations](/docs/customization/integrations) |
| [The agent](/docs/customization/tutorial/agent) | Tools that search recipes and read and update the user's profile, a prompt and the agent class | [Agents](/docs/agents/agent-architecture) |
| [The agentic execution](/docs/customization/tutorial/agentic-execution) | An execution definition with its input, prompt and validator | [Agentic execution](/docs/agents/agentic-execution) |

The tutorial shows the code and says what each part does. The linked pages describe the contracts behind it in full.

## Before you start

The tutorial builds on the [Suvereo starter](/docs/customization/using-the-suvereo-starter). Set it up as described in [Installation](/docs/getting-started/installation), and check that you can sign in. The starter runs the migrations and creates the starter roles on its first start, so nothing else needs to be prepared.

The starter ships with a finished diet advice domain definition in `server/src/diet_advice_domain/`, which is the same example as the tutorial. To build your own version from scratch, remove the shipped one:

1. Delete `server/src/diet_advice_domain/`.
2. In `server/config/settings_override.py`, delete the lines that refer to `diet_advice_domain`. The tutorial adds its own entries as it goes.

You need:

- An API key of a language model provider and of an embedding model provider, set up as described in [Managing data sets](/docs/management/data-sets). The starter reads the OpenAI key from `server/config/.env`, and the tutorial does not depend on a particular provider.
- A data set. Create one now in the UI if the instance has none.

## Create the package

A domain definition is a Django app, and it can be a standalone package. In the starter, your code is the package in `server/src/`, so this tutorial adds the domain definition there:

```
server/src/
├── pyproject.toml
└── diet_domain/
    ├── __init__.py
    └── apps.py
```

`server/src/pyproject.toml` declares the package. Change the name and add the package to it:

```toml
[tool.poetry]
name = "diet-domain"
version = "0.1.0"
description = "A domain definition for personalised nutrition, built in the Suvereo tutorial."
authors = ["Your Name <you@example.com>"]
packages = [{ include = "diet_domain" }]

[tool.poetry.dependencies]
python = "^3.10"
requests = ">=2.31.0"

[build-system]
requires = ["poetry-core"]
build-backend = "poetry.core.masonry.api"
```

The Suvereo server image already contains everything else the domain definition imports, so `requests` is the only dependency to declare:

| Package | Used for | Where it comes from |
|---|---|---|
| `suvereo_common` | The contracts a domain definition is written against: entities, retrievers, integrations, the builder and the agent. The domain definition does not import the server's code. | The server image |
| `pgvector` | The embedding column of the searchable entity. | The server image |
| `suvereo_agent_tool_calling` | `BaseToolCallingAgent`, the agent class used on the [agent page](/docs/customization/tutorial/agent). | The server image |
| `suvereo_agent_tools` | Ready-made tools, of which the tutorial uses the one that ends an execution. | The server image |
| `requests` | HTTP calls of the recipe source that reads a real API, at the end of the [integrations page](/docs/customization/tutorial/integrations#connecting-a-real-system). | `pyproject.toml` |

`diet_domain/__init__.py` is empty, and `apps.py` names the Django app:

```python
from django.apps import AppConfig


class DietDomainConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "diet_domain"
    verbose_name = "Diet Domain"
```

The starter builds `server/src/` into the image, so a change to the code takes effect after a rebuild:

```bash
docker compose up -d --build
```

The tutorial asks for a rebuild each time it registers something.

## What the tutorial simplifies

The snippets are a reduced version of a complete diet domain definition. Every part is present, but some pieces of a production domain definition are left out so that each page stays focused on the structure:

- Allergens are detected from a short list of keywords. A real domain definition would use a more complete list or a food database.
- The agent has three tools: reading and updating the user's profile, and searching recipes. A real assistant would have more, for example for logging what the user ate.

Continue with [the domain definition](/docs/customization/tutorial/domain-definition).
