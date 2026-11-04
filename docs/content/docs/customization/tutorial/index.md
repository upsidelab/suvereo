# Tutorial: Building a Vertical

This tutorial builds a [vertical](/docs/concepts#vertical) from an empty directory to a working feature. By the end, an instance of Suvereo knows about recipes and the people who eat them, a user can ask an [agent](/docs/concepts#agent) for meals that suit them, and an API call can return a validated meal plan for a week.

The example is a vertical for personalised nutrition, the **diet vertical**. It is one example of how a [domain](/docs/concepts#domain) can be described. The parts are the same for any other domain, so you can follow the tutorial as written and then replace recipes and diets with the data and systems of your own.

## What you will build

- **Data.** Two [entities](/docs/concepts#entity): `Recipe`, which is searchable by meaning, and `UserProfile`, which holds a person's allergies, dietary preferences and daily calorie target.
- **Integration types.** A recipe source and a user source: the kinds of external systems the vertical can import from.
- **Integrations.** A sample of each, which bring recipes and users into a [data set](/docs/concepts#data-set), and one that connects a real recipe API.
- **An agent.** A nutrition assistant that finds recipes for a user in a [conversation](/docs/concepts#conversation), using a tool that searches the recipes.
- **An agentic execution.** A weekly meal plan that runs in the background, started through the API, and is checked against the user's allergies and calorie target before it is returned.

## Pages

Each page builds on the previous one and leaves the instance in a working state.

| Page | Adds | Explained in |
|---|---|---|
| [The vertical](/docs/customization/tutorial/vertical) | Entities, the recipe retriever, the injector and builder, registration and migrations | [Verticals](/docs/customization/verticals) |
| [The integrations](/docs/customization/tutorial/integrations) | The recipe and user source types, their managers and two sample integrations | [Integrations](/docs/customization/integrations) |
| [The agent](/docs/customization/tutorial/agent) | A tool that searches recipes, a prompt and the agent class | [Agents](/docs/agents/agent-architecture) |
| [The agentic execution](/docs/customization/tutorial/agentic-execution) | An execution definition with its input, prompt and validator | [Agentic execution](/docs/agents/agentic-execution) |

The tutorial shows the code and says what each part does. The linked pages describe the contracts behind it in full.

## Before you start

The Suvereo starter, a repository for building on Suvereo, is not available yet (see [Using the Suvereo starter](/docs/customization/using-the-suvereo-starter)). Until it is, the tutorial extends a checkout of the Suvereo repository.

TODO: update once the Suvereo starter lands. This section, the package location and the install step in "Create the package" will need to be revisited to build on the starter instead of the Suvereo repository.

You need:

- The `server/` directory set up as described in its README: PostgreSQL with the pgvector extension, Redis, Poetry, migrations applied and an admin account created. Run `./manage.py seedroles` as well, so that the starter roles exist.
- The server, the Celery worker and the frontend running. The worker is needed by the sync and by the execution.
- An API key of a language model provider and of an embedding model provider, set up as described in [Managing data sets](/docs/management/data-sets). The tutorial does not depend on a particular provider.
- A data set. Create one now in the UI if the instance has none.

## Create the package

A vertical is a Django app, and it can be a standalone package. This tutorial creates one next to `server/`:

```
diet-vertical/
├── pyproject.toml
└── diet_vertical/
    ├── __init__.py
    └── apps.py
```

`pyproject.toml` declares the package and what it depends on:

```toml
[tool.poetry]
name = "diet-vertical"
version = "0.1.0"
description = "A vertical for personalised nutrition, built in the Suvereo tutorial."
authors = ["Your Name <you@example.com>"]
packages = [{ include = "diet_vertical" }]

[tool.poetry.dependencies]
python = "^3.11"
django = ">=5.2,<6.0"
pgvector = ">=0.4.1"
requests = ">=2.31.0"
suvereo-common = ">=1.7.0,<2.0.0"
suvereo-agent-tool-calling = ">=1.2.0"
suvereo-agent-tools = ">=1.0.0,<2.0.0"

[build-system]
requires = ["poetry-core"]
build-backend = "poetry.core.masonry.api"
```

| Dependency | Used for |
|---|---|
| `suvereo-common` | The contracts a vertical is written against: entities, retrievers, integrations, the builder and the agent. The vertical does not import the server's code. |
| `pgvector` | The embedding column of the searchable entity. |
| `requests` | HTTP calls of the recipe source that reads a real API, at the end of the [integrations page](/docs/customization/tutorial/integrations#connecting-a-real-system). |
| `suvereo-agent-tool-calling` | `BaseToolCallingAgent`, the agent class used on the [agent page](/docs/customization/tutorial/agent). |
| `suvereo-agent-tools` | Ready-made tools, of which the tutorial uses the one that ends an execution. |

`diet_vertical/__init__.py` is empty, and `apps.py` names the Django app:

```python
from django.apps import AppConfig


class DietVerticalConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "diet_vertical"
    verbose_name = "Diet Vertical"
```

Then install the package into the environment of the server in editable mode, so that edits take effect without reinstalling and so that `makemigrations` writes into your source directory:

```bash
cd server
poetry add --editable ../diet-vertical
```

If the package imports, the setup is done: `poetry run python -c "import diet_vertical"` prints nothing.

## What the tutorial simplifies

The snippets are a reduced version of a complete diet vertical. Every part is present, but some pieces of a production vertical are left out so that each page stays focused on the structure:

- Allergens are detected from a short list of keywords. A real vertical would use a more complete list or a food database.
- The agent has one tool, for searching recipes. It can be extended with tools that read and update the user's profile.

Continue with [the vertical](/docs/customization/tutorial/vertical).
