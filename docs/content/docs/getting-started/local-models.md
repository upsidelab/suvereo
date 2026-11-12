# Running with local models

Suvereo can run with no calls to external services: the language model and the embedding model both run on your own machine through [Ollama](/plugins/ollama), and everything else (PostgreSQL, Redis, the server and the frontend) runs in Docker Compose. Prompts, content and embeddings never leave your environment. This suits data that must stay in-house, such as patient records or confidential contracts.

## Install Ollama and pull models

[Install Ollama](https://ollama.com/download) on the host and pull a language model and an embedding model. For example:

```shell
ollama pull llama3.1
ollama pull nomic-embed-text
```

## Add the Ollama plugin

Add the plugin to the dependencies in `server/src/pyproject.toml` of the [Suvereo starter](/docs/customization/using-the-suvereo-starter):

```toml
suvereo-model-ollama = ">=2.0.0,<3.0.0"
```

Register its providers in `server/config/settings_override.py`. Keeping the OpenAI provider is not needed, and removing it means no OpenAI key is required:

```python
CATALOG_LANGUAGE_MODEL_PROVIDERS = [
    "suvereo_model_ollama.OllamaLanguageModelProvider",
]
CATALOG_EMBEDDING_PROVIDERS = [
    "suvereo_model_ollama.OllamaEmbeddingProvider",
]
```

## Point Suvereo at Ollama

The server runs in a container, so it reaches Ollama on the host through `host.docker.internal`. Set it in `server/config/.env`:

```
OLLAMA_HOST=http://host.docker.internal:11434
```

On Linux, add `extra_hosts: ["host.docker.internal:host-gateway"]` to the server, worker and beat services in `docker-compose.yml`. Ollama itself can also run as another container; then use its service name in `OLLAMA_HOST`.

Ollama needs no API key by default, because the models run on your machine, so leave the API key variables (`OPENAI_API_KEY`, `GOOGLE_API_KEY`, etc.) empty. Then build and start as described in [Installation](/docs/getting-started/installation).

## Select the models

When you [create a data set](/docs/management/data-sets), choose Ollama as the language model provider and as the embedding provider, then pick the models you pulled. Set the vector size to match the embedding model: the embedding settings cannot be changed after the data set is created.

## Other self-hosted models

Ollama is not the only option. Other self-hosted servers may expose an API that follows the same interface as one of the [model providers](/plugins), so the code of that provider can be reused with some adjustments, such as pointing it at your own server. Suvereo is open source, so you can adapt a plugin or write your own.
