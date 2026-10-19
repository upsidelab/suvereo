import logging
import mimetypes
import time

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
from agent.evaluation.judge_models_used_by_metrics import judge_models_used_by_metrics
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
EXECUTION_SUCCEEDED = "execution_succeeded"


class CaseRunner:
    """Runs one case against an opened target and scores it; each run gets its own conversation, mocks, trace and
    judge client, so one CaseRunner can be shared by parallel threads.

    judge_models_in_use are the judge models the suite's LLM metrics ask (see judge_models_used_by_metrics); worked out here when not given.
    """

    def __init__(
        self,
        loaded: LoadedSuite,
        target: BaseAgentTarget,
        pricing: PricingTable,
        judge_models_in_use: list[ModelTarget] | None = None,
    ):
        self.loaded = loaded
        self.target = target
        self.pricing = pricing
        self._mocks = MockIntegrationFactory(loaded.base_dir)
        self._scorer = RunScorer(loaded.base_dir)
        self._has_judge = bool(
            judge_models_used_by_metrics(loaded) if judge_models_in_use is None else judge_models_in_use
        )

    def run(
        self, case: EvalCase, model: ModelTarget | None = None, variant: PromptVariant | None = None, repeat: int = 1
    ) -> RunResult:
        """Run the case once and score it; an exception while setting up or running becomes the trace's error."""
        suite = self.loaded.suite
        recorder = TraceRecorder()
        duration_s = self._run_agent(case, model, variant, recorder)

        cost = self.pricing.trace_cost(recorder.trace)
        judge = EvalJudgeClient(suite.judge, self.pricing) if self._has_judge else None
        metrics, thresholds = self._scorer.score(
            suite.metrics_for(case),
            MetricContext(trace=recorder.trace, case=case, duration_s=duration_s, cost_usd=cost.usd, judge=judge),
        )
        judge_cost = judge.cost() if judge else TraceCost(usd=0.0)
        priced_spend = cost.priced_usd + judge_cost.priced_usd
        metrics[JUDGE_COST] = MetricResult(value=judge_cost.usd)
        return RunResult(
            case_id=case.id,
            model=model.display_label if model else "",
            variant=variant.name if variant else DEFAULT_VARIANT,
            repeat=repeat,
            passed=metrics[EXECUTION_SUCCEEDED].value is True
            and all(g.passed for g in thresholds.values() if g.required),
            metrics=metrics,
            thresholds=thresholds,
            unpriced_models=sorted(
                {
                    *cost.unpriced_models,
                    *cost.models_without_usage,
                    *judge_cost.unpriced_models,
                    *judge_cost.models_without_usage,
                }
            ),
            priced_spend_usd=priced_spend,
            trace=recorder.trace,
        )

    @staticmethod
    def errored_result(
        loaded: LoadedSuite,
        case: EvalCase,
        model: ModelTarget | None,
        variant: PromptVariant | None,
        repeat: int,
        error: str,
    ) -> RunResult:
        """A run that failed outside the agent, e.g. its sandbox could not be set up: the error in its trace, the
        auto metrics, and the suite's metrics with no value and missed thresholds, so every run has the same metric
        names."""
        trace = ExecutionTrace(error=error)
        metrics, thresholds = RunScorer(loaded.base_dir).scores_for_unfinished_run(
            loaded.suite.metrics_for(case), MetricContext(trace=trace, case=case), "the run did not complete"
        )
        metrics[JUDGE_COST] = MetricResult(value=0.0)
        return RunResult(
            case_id=case.id,
            model=model.display_label if model else "",
            variant=variant.name if variant else DEFAULT_VARIANT,
            repeat=repeat,
            passed=False,
            metrics=metrics,
            thresholds=thresholds,
            trace=trace,
        )

    def _run_agent(
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
                self.target.new_conversation(), self._config_overrides(model, variant), recorder
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
                conversation.copy_scratchpad_to_trace()
        return time.perf_counter() - started if started is not None else None

    def _attach_files(self, conversation: Conversation, case: EvalCase) -> None:
        service = ConversationFileAttachService()
        service.validate(self.target.agent, [path.name for path in case.files])
        for path in case.files:
            content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
            service.attach(conversation, path.name, path.read_bytes(), content_type)

    def _config_overrides(self, model: ModelTarget | None, variant: PromptVariant | None) -> AgentConfigOverrides:
        """This run's agent changes, never saved: the pinned model, the variant's prompt and config patch, trace
        handlers, and the resolver that answers integration lookups from mocks."""
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
