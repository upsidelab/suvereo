import logging
from typing import Any

from django.db import transaction
from django.utils import timezone
from suvereo_common.evaluation.mocks import BaseMockIntegration
from suvereo_common.utils import deep_merge

from agent.core.registries.agents.agent_registry import AgentRegistry
from agent.evaluation.integrations import IntegrationFixtureSyncer
from agent.models import Agent, Conversation
from agent.services import AgentPreconfigurationService
from catalog.models import DataSet
from catalog.services import DataSetDeletionService

logger = logging.getLogger(__name__)

NAME_LENGTH = DataSet._meta.get_field("name").max_length


class EvalSandbox:
    def __init__(self, data_set: DataSet, agent: Agent):
        self.data_set = data_set
        self.agent = agent

    @classmethod
    def create(
        cls, suite_name: str, agent_type: str, agent_config: dict[str, Any], integrations: list[BaseMockIntegration]
    ) -> "EvalSandbox":
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
        DataSetDeletionService.delete(self.data_set)

    def keep(self) -> None:
        self.data_set.is_temporary = False
        self.data_set.save(update_fields=["is_temporary"])
        Conversation.all_objects.filter(data_set=self.data_set).update(is_temporary=False)

    @staticmethod
    def _name(suite_name: str) -> str:
        stamp = f"{timezone.localtime():%m-%d %H:%M}"
        return f"Eval {suite_name[: NAME_LENGTH - len(stamp) - 6]} {stamp}"
