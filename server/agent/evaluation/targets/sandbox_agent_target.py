import logging
from typing import Any

from enthusiast_common.evaluation.mocks import BaseMockIntegration
from enthusiast_common.integrations import BaseIntegrationPluginResolver

from account.models import User
from agent.evaluation.sandbox import EvalSandbox
from agent.models import Agent

from .base_agent_target import BaseAgentTarget

logger = logging.getLogger(__name__)


class SandboxAgentTarget(BaseAgentTarget):
    """Tests an agent type on a temporary copy, so evaluation never touches real data (suite `agent: {type: ...}`).

    Opening creates an `__eval__` DataSet with a new agent of the type (default config plus the suite's
    agent_config) and syncs the mock integrations' data into it, e.g. a mock shop's catalog. Only those mocks
    answer; real integrations are never reached. Closing deletes the DataSet with everything the runs created,
    or with keep_run_data renames it `__kept__` for inspection.
    """

    def __init__(
        self,
        suite_name: str,
        agent_type: str,
        agent_config: dict[str, Any],
        integrations: list[BaseMockIntegration],
        user: User,
        keep_run_data: bool = False,
    ):
        super().__init__(user, keep_run_data)
        self.suite_name = suite_name
        self.agent_type = agent_type
        self.agent_config = agent_config
        self.integrations = integrations
        self.sandbox: EvalSandbox | None = None

    @property
    def real_resolver(self) -> type[BaseIntegrationPluginResolver] | None:
        return None

    def open(self) -> Agent:
        self.sandbox = EvalSandbox.create(self.suite_name, self.agent_type, self.agent_config, self.integrations)
        return self.sandbox.agent

    def close(self) -> None:
        """Destroy the sandbox, or keep it; a failure is logged so it never hides the run's error."""
        try:
            if self.sandbox is not None:
                self.sandbox.keep() if self.keep_run_data else self.sandbox.destroy()
        except Exception:
            logger.exception("Could not clean up evaluation sandbox %s", self.sandbox.data_set.name)
        finally:
            self.sandbox = None
            self._conversation_ids.clear()
