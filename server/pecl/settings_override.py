# Plugin entry point.
#
# A vertical installs itself on top of agentcore by editing (or shipping) this file.
# config/settings.py imports it and merges INSTALLED_VERTICALS into INSTALLED_APPS.
#
# Example — media vertical:
#

INSTALLED_VERTICALS = ["ecommerce_vertical"]

CATALOG_LANGUAGE_MODEL_PROVIDERS = ["enthusiast_model_openai.OpenAILanguageModelProvider"]
CATALOG_EMBEDDING_PROVIDERS      = ["enthusiast_model_openai.OpenAIEmbeddingProvider"]

AVAILABLE_AGENTS            = [
    'enthusiast_agent_product_search.ProductSearchAgent',
    'enthusiast_agent_user_manual_search.UserManualSearchAgent',
    'enthusiast_agent_order_intake.OrderIntakeAgent',
    'enthusiast_agent_catalog_enrichment.CatalogEnrichmentAgent',
]

AVAILABLE_AGENTIC_EXECUTION_DEFINITIONS = ['enthusiast_agent_order_intake.OrderIntakeAgenticExecutionDefinition']

CATALOG_INTEGRATION_PLUGINS = [
    "enthusiast_source_sample.SampleProductSource",
    "enthusiast_source_sample.SampleDocumentSource",
    'enthusiast_source_medusa.MedusaIntegration',
]
CATALOG_INTEGRATION_MANAGERS = [
    "ecommerce_vertical.sync.ProductSourceManager",
    "ecommerce_vertical.sync.DocumentSourceManager",
    "ecommerce_vertical.sync.ECommerceIntegrationManager",
]
CATALOG_ENTITY_PLUGINS      = [
    "ecommerce_vertical.models.Product",
    "ecommerce_vertical.models.Document",
]
#
# Out of the box (no vertical) agentcore runs standalone with these lists empty.
