# Plugin entry point.
#
# A vertical installs itself on top of agentcore by editing (or shipping) this file.
# config/settings.py imports it and merges INSTALLED_VERTICALS into INSTALLED_APPS.
#
# Example:
#
#     INSTALLED_VERTICALS = ["myvertical"]
#
#     AGENTCORE_LLM_PROVIDER_PLUGINS = ["agentcore_model_openai.OpenAILanguageModelProvider"]
#     AGENTCORE_AGENT_PLUGINS        = ["myvertical.agents.MyAgent"]
#     AGENTCORE_BUILDER_PLUGINS      = ["myvertical.builder.MyAgentBuilder"]
#     AGENTCORE_INTEGRATION_PLUGINS  = ["myvertical.integrations.MyIntegration"]
#     AGENTCORE_ENTITY_PLUGINS       = ["myvertical.models.MyEntity"]
#
# Out of the box (no vertical) agentcore runs standalone with these lists empty.
