import logging
import mimetypes
import time
from pathlib import Path

from enthusiast_common.config import AgentCallbackHandlerConfig, CallbackHandlerConfig
from enthusiast_common.evaluation.loaded_suite import LoadedSuite
from enthusiast_common.evaluation.metrics import MetricContext, MetricResult
from enthusiast_common.evaluation.suite import EvalCase, ModelTarget, PromptVariant
from enthusiast_common.evaluation.suite.prompt_variant import DEFAULT_VARIANT
from enthusiast_common.evaluation.trace import ExecutionTrace, TraceRecorder

from agent.agentic_execution.runner import AgenticExecutionRunner
from agent.conversation.services.conversation_file_attach_service import ConversationFileAttachService
from agent.core.agents.config_overrides import AgentConfigOverrides
from agent.evaluation.integrations import EvalIntegrationPluginResolver, MockIntegrationFactory
from agent.evaluation.judge_client import EvalJudgeClient
from agent.evaluation.pinned_llm import PinnedLLM
from agent.evaluation.pricing_table import PricingTable, TraceCost
from agent.evaluation.run_context import EvalRunContext
from agent.evaluation.targets import BaseAgentTarget
from agent.evaluation.trace_callback_handler import TraceCallbackHandler
from agent.models import Conversation

from .eval_execution_conversation import EvalExecutionConversation
from .run_result import RunResult
from .run_scorer import RunScorer

logger = logging.getLogger(__name__)

JUDGE_COST = "judge_cost_usd"
SUCCEEDED = "execution_succeeded"


class CaseRunner:
    """Runs a suite's cases one at a time against an opened target, each in a fresh conversation with fresh mocks."""

    def __init__(self, loaded: LoadedSuite, target: BaseAgentTarget, pricing: PricingTable):
        self.loaded = loaded
        self.target = target
        self.pricing = pricing
        self._mocks = MockIntegrationFactory(loaded.base_dir)
        self._scorer = RunScorer(loaded.base_dir)

    def run(
        self, case: EvalCase, model: ModelTarget | None = None, variant: PromptVariant | None = None, repeat: int = 1
    ) -> RunResult:
        """Run the case once and score it; an exception while setting up or running becomes the trace's error."""
        suite = self.loaded.suite
        recorder = TraceRecorder()
        duration_s = self._execute(case, model, variant, recorder)

        cost = self.pricing.trace_cost(recorder.trace)
        judge = EvalJudgeClient(suite.judge, self.pricing) if suite.judge else None
        metrics, gates = self._scorer.score(
            suite.metrics_for(case),
            MetricContext(trace=recorder.trace, case=case, duration_s=duration_s, cost_usd=cost.usd, judge=judge),
        )
        judge_cost = judge.cost() if judge else TraceCost(usd=0.0)
        metrics[JUDGE_COST] = MetricResult(value=judge_cost.usd)
        return RunResult(
            case_id=case.id,
            model=model.display_label if model else "",
            variant=variant.name if variant else DEFAULT_VARIANT,
            repeat=repeat,
            passed=metrics[SUCCEEDED].value is True and all(g.passed for g in gates.values() if g.required),
            metrics=metrics,
            gates=gates,
            unpriced_models=sorted({*cost.unpriced_models, *judge_cost.unpriced_models}),
            trace=recorder.trace,
        )

    @staticmethod
    def errored(
        case: EvalCase, model: ModelTarget | None, variant: PromptVariant | None, repeat: int, error: str
    ) -> RunResult:
        """A run that never started, e.g. because its sandbox could not be set up, with its auto metrics."""
        trace = ExecutionTrace(error=error)
        metrics, _ = RunScorer(Path.cwd()).score([], MetricContext(trace=trace, case=case))
        metrics[JUDGE_COST] = MetricResult(value=0.0)
        return RunResult(
            case_id=case.id,
            model=model.display_label if model else "",
            variant=variant.name if variant else DEFAULT_VARIANT,
            repeat=repeat,
            passed=False,
            metrics=metrics,
            gates={},
            trace=trace,
        )

    def _execute(
        self, case: EvalCase, model: ModelTarget | None, variant: PromptVariant | None, recorder: TraceRecorder
    ) -> float | None:
        """Set up and run the case, recording any exception as the trace's error; returns the agent's run time."""
        conversation, started = None, None
        try:
            integrations = [self._mocks.build(config) for config in self.loaded.suite.integrations_for(case)]
            for integration in integrations:
                integration.recorder = recorder
            context = EvalRunContext(recorder, integrations, self.target.real_resolver, self.loaded.base_dir)
            conversation = EvalExecutionConversation(
                self.target.new_conversation(), self._overrides(model, variant), recorder
            )
            self._attach_files(conversation.conversation, case)
            with context.activate():
                started = time.perf_counter()
                result = AgenticExecutionRunner().run(
                    self.loaded.suite.execution_key, case.input, conversation, conversation.record_attempt
                )
            recorder.trace.execution_result = result
            recorder.trace.output = result.output if result.success else None
        except Exception as e:
            logger.warning("Evaluation case %s raised", case.id, exc_info=True)
            recorder.trace.error = f"{type(e).__name__}: {e}"
        finally:
            if conversation is not None:
                conversation.record_scratchpad()
        return time.perf_counter() - started if started is not None else None

    def _attach_files(self, conversation: Conversation, case: EvalCase) -> None:
        service = ConversationFileAttachService()
        service.validate(self.target.agent, [path.name for path in case.files])
        for path in case.files:
            content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
            service.attach(conversation, path.name, path.read_bytes(), content_type)

    def _overrides(self, model: ModelTarget | None, variant: PromptVariant | None) -> AgentConfigOverrides:
        system_prompt = None
        if variant and variant.system_prompt_file:
            system_prompt = (self.loaded.base_dir / variant.system_prompt_file).read_text(encoding="utf-8")
        return AgentConfigOverrides(
            llm_class=PinnedLLM.for_model(model.provider, model.model) if model else None,
            llm_callbacks=[CallbackHandlerConfig(handler_class=TraceCallbackHandler)],
            agent_callback_handler=AgentCallbackHandlerConfig(handler_class=TraceCallbackHandler),
            integration_plugin_resolver=EvalIntegrationPluginResolver,
            system_prompt=system_prompt,
            agent_config_patch=variant.agent_config if variant else None,
        )
