# Plugin entry point.
#
# A domain definition installs itself on top of Suvereo by editing (or shipping) this file.
# pecl/settings.py imports it (`from pecl.settings_override import *`) and merges
# INSTALLED_DOMAIN_DEFINITIONS into INSTALLED_APPS.
#
# Out of the box (no domain definition) Suvereo runs standalone, so every list here is empty.
#
# Example — Enthusiast (an eCommerce domain definition) would set:
#
#     INSTALLED_DOMAIN_DEFINITIONS = ["enthusiast_domain"]
#     AVAILABLE_AGENTIC_EXECUTION_DEFINITIONS = [
#         "enthusiast_agent_catalog_enrichment.CatalogEnrichmentAgenticExecutionDefinition",
#     ]
#     CATALOG_INTEGRATION_PLUGINS = [
#         "enthusiast_source_sample.SampleProductSource",
#         "enthusiast_source_medusa.MedusaIntegration",
#     ]
#     CATALOG_INTEGRATION_MANAGERS = [
#         "enthusiast_domain.sync.ProductSourceManager",
#         "enthusiast_domain.sync.DocumentSourceManager",
#         "enthusiast_domain.sync.ECommerceIntegrationManager",
#     ]
#     CATALOG_ENTITY_PLUGINS = [
#         "enthusiast_domain.models.Product",
#         "enthusiast_domain.models.Document",
#     ]

INSTALLED_DOMAIN_DEFINITIONS = []

AVAILABLE_AGENTS = []
AVAILABLE_AGENTIC_EXECUTION_DEFINITIONS = []

CATALOG_INTEGRATION_PLUGINS = []
CATALOG_INTEGRATION_MANAGERS = []
CATALOG_ENTITY_PLUGINS = []
