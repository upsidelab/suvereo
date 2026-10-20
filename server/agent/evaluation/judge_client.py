from threading import Lock

from enthusiast_common.evaluation.metrics import BaseJudgeClient
from enthusiast_common.evaluation.suite import ModelTarget
from enthusiast_common.evaluation.trace import TraceRecorder
from langchain_core.language_models import BaseChatModel

from agent.core.registries.language_models import LanguageModelRegistry
from agent.evaluation.pricing_table import PricingTable, TraceCost
from agent.evaluation.trace_callback_handler import TraceCallbackHandler


class EvalJudgeClient(BaseJudgeClient):
    """Sends LLM metrics' judge prompts to the judge model and records every judge call in its own trace for costing.

    target is the suite's judge; a metric may name another model per call. Each model's LLM is built on first use,
    and a model's own pricing (ModelTarget.pricing) is added to the table then. Judge cost stays apart from the agent's.
    """

    def __init__(self, target: ModelTarget | None, pricing: PricingTable):
        self.target = target
        self._pricing = pricing
        self._recorder = TraceRecorder()
        self._llms: dict[tuple[str, str], BaseChatModel] = {}
        self._lock = Lock()

    def complete(self, prompt: str, model: ModelTarget | None = None) -> str:
        """Ask the metric's judge model, or else the suite's; raises ValueError when neither is set."""
        target = model or self.target
        if target is None:
            raise ValueError("No judge model: set 'judge' in the suite or in the metric's params.")
        return self._llm_for(target).invoke(prompt).text

    def cost(self) -> TraceCost:
        """What every judge model has cost so far."""
        return self._pricing.trace_cost(self._recorder.trace)

    def _llm_for(self, target: ModelTarget) -> BaseChatModel:
        """The LLM for a judge model, built once and shared by every metric naming it."""
        key = (target.provider, target.model)
        with self._lock:
            if key not in self._llms:
                if target.pricing is not None:
                    self._pricing = self._pricing.with_overrides({target.model: target.pricing})
                provider_class = LanguageModelRegistry().provider_class_by_name(target.provider)
                self._llms[key] = provider_class(target.model).provide_language_model(
                    callbacks=[TraceCallbackHandler(self._recorder)]
                )
            return self._llms[key]
