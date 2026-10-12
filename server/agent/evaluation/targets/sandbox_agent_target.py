from typing import Any

from enthusiast_common.evaluation.mocks import BaseMockIntegration
from enthusiast_common.integrations import BaseIntegrationPluginResolver

from account.models import User
from agent.evaluation.sandbox import EvalSandbox
from agent.models import Agent

from .base_agent_target import BaseAgentTarget


class SandboxAgentTarget(BaseAgentTarget):
    """An agent type run in a throwaway sandbox filled from the suite's mock integrations; never real ones."""

    def __init__(
        self,
        suite_name: str,
        agent_type: str,
        agent_config: dict[str, Any],
        integrations: list[BaseMockIntegration],
        user: User,
        keep_conversations: bool = False,
    ):
        super().__init__(user, keep_conversations)
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
        if self.sandbox is not None:
            if self.keep_conversations:
                self.sandbox.keep()
            else:
                self.sandbox.destroy()
            self.sandbox = None
        self._conversation_ids.clear()
