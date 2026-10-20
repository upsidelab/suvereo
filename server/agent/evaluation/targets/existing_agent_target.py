from enthusiast_common.integrations import BaseIntegrationPluginResolver

from account.models import User
from agent.models import Agent
from catalog.integrations.resolver import IntegrationPluginResolver

from .base_agent_target import BaseAgentTarget


class ExistingAgentTarget(BaseAgentTarget):
    """Tests an agent you already configured, on its real DataSet (suite `agent: {id: ...}`).

    The agent's stored config is never changed; overrides apply per run only. Mocks answer integration lookups, and
    real integrations are reached only with allow_real_integrations. Closing deletes the runs' conversations,
    or with keep_run_data marks them kept.
    """

    def __init__(self, agent_id: int, user: User, allow_real_integrations: bool = False, keep_run_data: bool = False):
        super().__init__(user, keep_run_data)
        self.agent_id = agent_id
        self.allow_real_integrations = allow_real_integrations

    @property
    def real_resolver(self) -> type[BaseIntegrationPluginResolver] | None:
        return IntegrationPluginResolver if self.allow_real_integrations else None

    def open(self) -> Agent:
        return Agent.objects.select_related("dataset").get(pk=self.agent_id)
