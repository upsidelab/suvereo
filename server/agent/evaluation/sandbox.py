import logging
import re
import secrets
import time
from typing import Any

from django.db import transaction
from enthusiast_common.evaluation.mocks import BaseMockIntegration
from enthusiast_common.utils import deep_merge

from agent.core.registries.agents.agent_registry import AgentRegistry
from agent.evaluation.eval_conversations import EvalConversations
from agent.evaluation.integrations import IntegrationFixtureSyncer
from agent.models import Agent, Conversation
from agent.services import AgentPreconfigurationService
from catalog.models import DataSet

logger = logging.getLogger(__name__)

NAME_PREFIX = "__eval__"
#: Same length as NAME_PREFIX, so a kept sandbox's name still fits; purge_stale never matches it.
KEPT_PREFIX = "__kept__"
NAME_LENGTH = 30
STALE_AFTER_SECONDS = 6 * 60 * 60
CREATED_AT = re.compile(rf"^{NAME_PREFIX}([0-9a-f]+)-")


class EvalSandbox:
    """A throwaway DataSet and agent for one suite, filled from its mock integrations and deleted afterwards."""

    def __init__(self, data_set: DataSet, agent: Agent):
        self.data_set = data_set
        self.agent = agent

    @classmethod
    def create(
        cls, suite_name: str, agent_type: str, agent_config: dict[str, Any], integrations: list[BaseMockIntegration]
    ) -> "EvalSandbox":
        """Create the sandbox and sync the integrations' fixture data into it; anything half-built is removed on failure."""
        cls.purge_stale()
        agent_class = AgentRegistry().get_agent_class_by_type(agent_type)
        config = deep_merge(AgentPreconfigurationService.default_agent_configuration(agent_class), agent_config)
        with transaction.atomic():
            data_set = DataSet.objects.create(name=cls._name(suite_name))
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
        except BaseException:
            sandbox.destroy()
            raise
        return sandbox

    def destroy(self) -> None:
        """Delete the DataSet and everything in it, conversations included."""
        EvalConversations.delete(Conversation.objects.filter(data_set=self.data_set))
        self.data_set.delete()

    def keep(self) -> None:
        """Rename the sandbox so purge_stale leaves it, and its conversations, for someone to inspect."""
        self.data_set.name = KEPT_PREFIX + self.data_set.name.removeprefix(NAME_PREFIX)
        self.data_set.save(update_fields=["name"])

    @classmethod
    def purge_stale(cls) -> int:
        """Delete sandboxes left behind by runs that died, sparing young ones; one that fails is logged and skipped."""
        purged = 0
        for data_set in DataSet.objects.filter(name__startswith=NAME_PREFIX):
            match = CREATED_AT.match(data_set.name)
            if not match or time.time() - int(match.group(1), 16) <= STALE_AFTER_SECONDS:
                continue
            try:
                cls(data_set, None).destroy()
            except Exception:
                logger.warning("Could not purge stale evaluation sandbox %s", data_set.name, exc_info=True)
                continue
            purged += 1
        return purged

    @staticmethod
    def _name(suite_name: str) -> str:
        slug = re.sub(r"[^a-z0-9]+", "-", suite_name.lower()).strip("-")
        return f"{NAME_PREFIX}{int(time.time()):x}-{secrets.token_hex(2)}-{slug}"[:NAME_LENGTH]
