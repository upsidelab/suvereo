from enthusiast_common.integrations import BaseIntegrationPluginResolver

from account.models import User
from agent.models import Agent
from catalog.integrations.resolver import IntegrationPluginResolver

from .base_agent_target import BaseAgentTarget


class ExistingAgentTarget(BaseAgentTarget):
    """An agent already configured on a DataSet, used as it is; its stored config is never changed."""

    def __init__(
        self, agent_id: int, user: User, allow_real_integrations: bool = False, keep_conversations: bool = False
    ):
        super().__init__(user, keep_conversations)
        self.agent_id = agent_id
        self.allow_real_integrations = allow_real_integrations

    @property
    def real_resolver(self) -> type[BaseIntegrationPluginResolver] | None:
        return IntegrationPluginResolver if self.allow_real_integrations else None

    def open(self) -> Agent:
        return Agent.objects.select_related("dataset").get(pk=self.agent_id)
