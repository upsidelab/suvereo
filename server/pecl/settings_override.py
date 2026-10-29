# Plugin entry point.
#
# A vertical installs itself on top of Suvereo by editing (or shipping) this file.
# pecl/settings.py imports it (`from pecl.settings_override import *`) and merges
# INSTALLED_VERTICALS into INSTALLED_APPS.
#
# Out of the box (no vertical) Suvereo runs standalone, so every list here is empty.
#
# Example — Enthusiast (an eCommerce vertical) would set:
#
#     INSTALLED_VERTICALS = ["enthusiast_vertical"]
#     AVAILABLE_AGENTIC_EXECUTION_DEFINITIONS = [
#         "enthusiast_agent_catalog_enrichment.CatalogEnrichmentAgenticExecutionDefinition",
#     ]
#     CATALOG_INTEGRATION_PLUGINS = [
#         "enthusiast_source_sample.SampleProductSource",
#         "enthusiast_source_medusa.MedusaIntegration",
#     ]
#     CATALOG_INTEGRATION_MANAGERS = [
#         "enthusiast_vertical.sync.ProductSourceManager",
#         "enthusiast_vertical.sync.DocumentSourceManager",
#         "enthusiast_vertical.sync.ECommerceIntegrationManager",
#     ]
#     CATALOG_ENTITY_PLUGINS = [
#         "enthusiast_vertical.models.Product",
#         "enthusiast_vertical.models.Document",
#     ]

INSTALLED_VERTICALS = []

AVAILABLE_AGENTS = []
AVAILABLE_AGENTIC_EXECUTION_DEFINITIONS = []

CATALOG_INTEGRATION_PLUGINS = []
CATALOG_INTEGRATION_MANAGERS = []
CATALOG_ENTITY_PLUGINS = []
