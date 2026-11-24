from abc import ABC, abstractmethod

from suvereo_common.evaluation.base_model_client import BaseModelClient
from suvereo_common.evaluation.suite import EvalCase
from suvereo_common.evaluation.trace import TraceRecorder

from agent.core.agents.config_overrides import AgentConfigOverrides
from agent.models import Conversation


class BaseRunDriver(ABC):
    @abstractmethod
    def run(
        self,
        case: EvalCase,
        conversation: Conversation,
        overrides: AgentConfigOverrides,
        recorder: TraceRecorder,
        user_llm: BaseModelClient | None = None,
    ) -> None:
        pass
