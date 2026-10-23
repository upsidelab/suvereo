from abc import ABC, abstractmethod

from enthusiast_common.evaluation.suite import EvalCase
from enthusiast_common.evaluation.trace import TraceRecorder

from agent.core.agents.config_overrides import AgentConfigOverrides
from agent.models import Conversation


class BaseRunDriver(ABC):
    """Drives the agent through one case on a prepared conversation, recording what happened into the trace; raises
    when the run cannot go on."""

    @abstractmethod
    def run(
        self, case: EvalCase, conversation: Conversation, overrides: AgentConfigOverrides, recorder: TraceRecorder
    ) -> None:
        """Run the case, filling the trace's output and the kind's own record (attempts or turns)."""
