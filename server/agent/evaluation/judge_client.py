from enthusiast_common.evaluation.metrics import BaseJudgeClient
from enthusiast_common.evaluation.suite import ModelTarget
from enthusiast_common.evaluation.trace import TraceRecorder

from agent.core.registries.language_models import LanguageModelRegistry
from agent.evaluation.pricing_table import PricingTable, TraceCost
from agent.evaluation.trace_callback_handler import TraceCallbackHandler


class EvalJudgeClient(BaseJudgeClient):
    """The judge model LLM metrics ask, with its own trace so judge cost stays apart from the agent's."""

    def __init__(self, target: ModelTarget, pricing: PricingTable):
        self.target = target
        self._pricing = pricing
        self._recorder = TraceRecorder()
        provider_class = LanguageModelRegistry().provider_class_by_name(target.provider)
        self._llm = provider_class(target.model).provide_language_model(
            callbacks=[TraceCallbackHandler(self._recorder)]
        )

    def complete(self, prompt: str) -> str:
        return self._llm.invoke(prompt).text

    def cost(self) -> TraceCost:
        """What the judge has cost so far."""
        return self._pricing.trace_cost(self._recorder.trace)
