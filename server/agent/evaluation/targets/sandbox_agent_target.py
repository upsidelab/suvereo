import logging
from typing import Any

from suvereo_common.evaluation.mocks import BaseMockIntegration
from suvereo_common.integrations import BaseIntegrationPluginResolver

from account.models import User
from agent.evaluation.sandbox import EvalSandbox
from agent.evaluation.targets.base_agent_target import BaseAgentTarget
from agent.models import Agent

logger = logging.getLogger(__name__)


class SandboxAgentTarget(BaseAgentTarget):
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
        try:
            if self.sandbox is not None:
                self.sandbox.keep() if self.keep_run_data else self.sandbox.destroy()
        except Exception:
            logger.exception("Could not clean up evaluation sandbox %s", self.sandbox.data_set.name)
        finally:
            self.sandbox = None
            self._conversation_ids.clear()
