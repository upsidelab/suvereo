import json
import logging
import tempfile
import threading
from concurrent.futures import ThreadPoolExecutor
from contextlib import ExitStack, contextmanager, nullcontext
from datetime import datetime
from itertools import product
from typing import Iterator

from django.db import connection
from django.test import override_settings
from suvereo_common.evaluation.errors import EvalSuiteError
from suvereo_common.evaluation.loaded_suite import LoadedSuite
from suvereo_common.evaluation.suite import EvalCase, ModelTarget, PromptVariant

from agent.evaluation.eval_user import EvalUser
from agent.evaluation.integrations import MockIntegrationFactory
from agent.evaluation.judge_models_used_by_metrics import judge_models_used_by_metrics
from agent.evaluation.pricing_table import PricingTable
from agent.evaluation.targets import BaseAgentTarget, ExistingAgentTarget, SandboxAgentTarget
from agent.evaluation.user_model_in_use import user_model_in_use

from .case_runner import CaseRunner
from .run_result import RunResult
from .suite_run_options import SuiteRunOptions
from .suite_run_result import StopReason, SuiteRunResult

logger = logging.getLogger(__name__)

PlannedRun = tuple[EvalCase, ModelTarget | None, PromptVariant | None, int]


class SuiteRunner:
    """Runs a loaded suite's models x variants x cases x repeats, in parallel if asked, until its budget runs out."""

    def __init__(
        self, loaded: LoadedSuite, options: SuiteRunOptions | None = None, pricing: PricingTable | None = None
    ):
        self.loaded = loaded
        self.options = options or SuiteRunOptions()
        self.judge_models_in_use = judge_models_used_by_metrics(loaded)
        self.user_model_in_use = user_model_in_use(loaded)
        self.pricing = (pricing or PricingTable.load()).with_overrides(self._suite_price_overrides())
        self._lock = threading.Lock()
        self._spent = 0.0
        self._stopped_reason: StopReason | None = None

    @property
    def budget_usd(self) -> float | None:
        return self.options.budget_usd or self.loaded.suite.budget_usd

    @property
    def planned_run_count(self) -> int:
        """How many runs the suite plans: models x variants (with the default) x cases x repeats."""
        return len(self._planned_runs(self.loaded.cases))

    def run(self) -> SuiteRunResult:
        """Run every planned run; raises EvalSuiteError when a budget is set but a model under test has no price."""
        self._check_budget_is_trackable()
        self._spent, self._stopped_reason = 0.0, None
        self._warn_on_self_judging()
        started_at = datetime.now()
        results: list[RunResult] = []
        with self._run_files_media_root():
            for cases in self._cases_by_sandbox():
                results += self._run_group(cases)
        return SuiteRunResult(
            suite=self.loaded.suite.name,
            planned_runs=self.planned_run_count,
            runs=results,
            spent_usd=self._spent,
            stopped_reason=self._stopped_reason,
            unpriced_models=sorted({model for result in results for model in result.unpriced_models}),
            budget_usd=self.budget_usd,
            pricing_as_of=self.pricing.as_of,
            started_at=started_at,
            finished_at=datetime.now(),
        )

    def _run_group(self, cases: list[EvalCase]) -> list[RunResult]:
        """Run cases sharing a sandbox; if it cannot be set up, their runs are recorded as errored and the suite goes on."""
        with ExitStack() as stack:
            try:
                target = stack.enter_context(self._target_for_group(cases))
            except Exception as e:
                ids = ", ".join(case.id for case in cases)
                logger.warning("Setting up the agent for case(s) %s failed", ids, exc_info=True)
                error = f"Setting up the agent for case(s) {ids} failed: {type(e).__name__}: {e}"
                return [
                    CaseRunner.errored_result(self.loaded, *planned, error) for planned in self._planned_runs(cases)
                ]
            runner = CaseRunner(self.loaded, target, self.pricing, self.judge_models_in_use)
            return self._run_planned(runner, self._planned_runs(cases))

    def _planned_runs(self, cases: list[EvalCase]) -> list[PlannedRun]:
        suite = self.loaded.suite
        models = suite.models or [None]
        variants = [None, *suite.variants]
        repeats = range(1, suite.repeats + 1)
        return [
            (case, model, variant, repeat) for model, variant, case, repeat in product(models, variants, cases, repeats)
        ]

    def _run_planned(self, runner: CaseRunner, plan: list[PlannedRun]) -> list[RunResult]:
        if self.options.parallel == 1:
            results = [self._run_within_budget(runner, planned) for planned in plan]
        else:
            with ThreadPoolExecutor(max_workers=self.options.parallel) as pool:
                results = list(pool.map(lambda planned: self._run_in_thread(runner, planned), plan))
        return [result for result in results if result is not None]

    def _run_in_thread(self, runner: CaseRunner, planned: PlannedRun) -> RunResult | None:
        try:
            return self._run_within_budget(runner, planned)
        finally:
            connection.close()

    def _run_within_budget(self, runner: CaseRunner, planned: PlannedRun) -> RunResult | None:
        """Run one planned run, or skip it and return None once the run has stopped (budget spent or untracked).

        A failure outside the agent (which CaseRunner already records in the trace) becomes an errored run.
        """
        budget = self.budget_usd
        with self._lock:
            if budget is not None and self._spent >= budget and self._stopped_reason is None:
                self._stopped_reason = "budget_spent"
            if self._stopped_reason is not None:
                return None
        try:
            result = runner.run(*planned)
        except Exception as e:
            logger.exception("Run of case %s failed outside the agent", planned[0].id)
            return CaseRunner.errored_result(self.loaded, *planned, f"The run failed: {type(e).__name__}: {e}")
        with self._lock:
            self._spent += result.priced_spend_usd
            if budget is not None and result.unpriced_models and self._stopped_reason is None:
                logger.warning(
                    "Unpriced model(s) %s; stopping, as the budget cannot be tracked.", result.unpriced_models
                )
                self._stopped_reason = "budget_untracked"
        return result

    def _cases_by_sandbox(self) -> list[list[EvalCase]]:
        """Cases grouped by the integration data their sandbox is synced from; one group for an existing agent."""
        if not self.loaded.suite.agent.is_sandbox:
            return [self.loaded.cases]
        groups: dict[str, list[EvalCase]] = {}
        for case in self.loaded.cases:
            data = {i.key: i.config.get("data") for i in self.loaded.suite.integrations_for(case)}
            groups.setdefault(json.dumps(data, sort_keys=True, default=str), []).append(case)
        return list(groups.values())

    def _target_for_group(self, cases: list[EvalCase]) -> BaseAgentTarget:
        """An unopened target for cases sharing integration data: a sandbox built from it, or the existing agent."""
        case = cases[0]
        suite, user, keep = self.loaded.suite, EvalUser.get(), self.options.keep_run_data
        if not suite.agent.is_sandbox:
            return ExistingAgentTarget(suite.agent.id, user, self.options.allow_real_integrations, keep)
        factory = MockIntegrationFactory(self.loaded.base_dir)
        integrations = [factory.build(config) for config in suite.integrations_for(case)]
        return SandboxAgentTarget(suite.name, suite.agent.type, suite.agent.config, integrations, user, keep)

    def _run_files_media_root(self):
        """A temporary MEDIA_ROOT for the run's files, unless the run data, and so its files, are kept."""
        return nullcontext() if self.options.keep_run_data else self._temporary_media_root()

    @staticmethod
    @contextmanager
    def _temporary_media_root() -> Iterator[None]:
        with tempfile.TemporaryDirectory(prefix="eval-media-") as media_root:
            with override_settings(MEDIA_ROOT=media_root):
                yield

    def _check_budget_is_trackable(self) -> None:
        targets = [*self.loaded.suite.models, *self.judge_models_in_use, *self._user_models()]
        unpriced = sorted({t.model for t in targets if self.pricing.price_for(t.model) is None})
        if self.budget_usd is not None and unpriced:
            raise EvalSuiteError(
                f"A budget is set but {', '.join(unpriced)} has no price; add 'pricing' to the model in the suite."
            )

    def _suite_price_overrides(self) -> dict:
        targets = [*self.loaded.suite.models, *self.judge_models_in_use, *self._user_models()]
        return {target.model: target.pricing for target in targets if target.pricing}

    def _user_models(self) -> list[ModelTarget]:
        return [self.user_model_in_use] if self.user_model_in_use else []

    def _warn_on_self_judging(self) -> None:
        for judge in self.judge_models_in_use:
            if any(m.provider == judge.provider and m.model == judge.model for m in self.loaded.suite.models):
                logger.warning(
                    "The judge %s is also a model under test; it tends to favour its own answers.", judge.model
                )
