import logging
from typing import Any

from django.db import transaction
from django.utils import timezone
from enthusiast_common.evaluation.mocks import BaseMockIntegration
from enthusiast_common.utils import deep_merge

from agent.core.registries.agents.agent_registry import AgentRegistry
from agent.evaluation.integrations import IntegrationFixtureSyncer
from agent.models import Agent, Conversation
from agent.services import AgentPreconfigurationService
from catalog.models import DataSet
from catalog.services import DataSetDeletionService

logger = logging.getLogger(__name__)

NAME_LENGTH = DataSet._meta.get_field("name").max_length


class EvalSandbox:
    """A temporary DataSet (is_temporary, so hidden from the API) and agent for one suite, filled from its mock
    integrations and deleted afterwards."""

    def __init__(self, data_set: DataSet, agent: Agent):
        self.data_set = data_set
        self.agent = agent

    @classmethod
    def create(
        cls, suite_name: str, agent_type: str, agent_config: dict[str, Any], integrations: list[BaseMockIntegration]
    ) -> "EvalSandbox":
        """Create the sandbox and sync the integrations' fixture data into it; anything half-built is removed on failure.

        The sync calls the integrations' mocks, so they are reset afterwards and runs start from a fresh state.
        """
        agent_class = AgentRegistry().get_agent_class_by_type(agent_type)
        config = deep_merge(AgentPreconfigurationService.default_agent_configuration(agent_class), agent_config)
        with transaction.atomic():
            data_set = DataSet.objects.create(name=cls._name(suite_name), is_temporary=True)
            agent = Agent.objects.create(
                name=f"Evaluation: {suite_name}"[:255],
                agent_type=agent_type,
                config=config,
                dataset=data_set,
                file_upload=True,
            )
        sandbox = cls(data_set, agent)
        try:
            for integration in integrations:
                IntegrationFixtureSyncer().sync(integration, data_set)
                integration.reset_mocks()
        except BaseException:
            sandbox.destroy()
            raise
        return sandbox

    def destroy(self) -> None:
        """Delete the DataSet and everything in it, conversations included."""
        DataSetDeletionService.delete(self.data_set)

    def keep(self) -> None:
        """Turn the sandbox and its conversations into regular, listed ones, so the purges leave them for someone to
        inspect."""
        self.data_set.is_temporary = False
        self.data_set.save(update_fields=["is_temporary"])
        Conversation.all_objects.filter(data_set=self.data_set).update(is_temporary=False)

    @staticmethod
    def _name(suite_name: str) -> str:
        """e.g. "Eval order-intake 10-20 14:03", the suite name cut to fit; shown once a sandbox is kept."""
        stamp = f"{timezone.localtime():%m-%d %H:%M}"
        return f"Eval {suite_name[: NAME_LENGTH - len(stamp) - 6]} {stamp}"
