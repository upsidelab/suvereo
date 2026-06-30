# Plugin entry point.
#
# A vertical installs itself on top of agentcore by editing (or shipping) this file.
# config/settings.py imports it and merges INSTALLED_VERTICALS into INSTALLED_APPS.
#
# Example:
#
#     INSTALLED_VERTICALS = ["myvertical"]
#
#     CATALOG_LANGUAGE_MODEL_PROVIDERS = ["enthusiast_model_openai.OpenAILanguageModelProvider"]
#     CATALOG_EMBEDDING_PROVIDERS      = ["enthusiast_model_openai.OpenAIEmbeddingProvider"]
#     AVAILABLE_AGENTS                 = ["myvertical.agents.MyAgent"]
#     CATALOG_INTEGRATION_PLUGINS      = ["myvertical.integrations.MyIntegration"]
#     CATALOG_INTEGRATION_MANAGERS     = ["myvertical.sync.MyIntegrationManager"]
#     CATALOG_ENTITY_PLUGINS           = ["myvertical.models.MyEntity"]
#
# Out of the box (no vertical) agentcore runs standalone with these lists empty.
