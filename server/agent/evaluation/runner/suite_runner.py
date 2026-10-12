import json
import logging
import tempfile
import threading
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager, nullcontext
from itertools import product
from typing import Iterator

from django.db import connection
from django.test import override_settings
from enthusiast_common.evaluation.errors import EvalSuiteError
from enthusiast_common.evaluation.loaded_suite import LoadedSuite
from enthusiast_common.evaluation.suite import EvalCase, ModelTarget, PromptVariant

from agent.evaluation.eval_user import EvalUser
from agent.evaluation.integrations import MockIntegrationFactory
from agent.evaluation.pricing_table import PricingTable
from agent.evaluation.targets import BaseAgentTarget, ExistingAgentTarget, SandboxAgentTarget

from .case_runner import JUDGE_COST, CaseRunner
from .run_result import RunResult
from .suite_run_options import SuiteRunOptions
from .suite_run_result import SuiteRunResult

logger = logging.getLogger(__name__)

COST = "cost_usd"
PlannedRun = tuple[EvalCase, ModelTarget | None, PromptVariant | None, int]


class SuiteRunner:
    """Runs a loaded suite's models x variants x cases x repeats, in parallel if asked, until its budget runs out."""

    def __init__(
        self, loaded: LoadedSuite, options: SuiteRunOptions | None = None, pricing: PricingTable | None = None
    ):
        self.loaded = loaded
        self.options = options or SuiteRunOptions()
        self.pricing = (pricing or PricingTable.load()).with_overrides(self._suite_prices())
        self._lock = threading.Lock()
        self._spent = 0.0
        self._budget_exceeded = False
        self._budget_untracked = False

    @property
    def budget_usd(self) -> float | None:
        return self.options.budget_usd or self.loaded.suite.budget_usd

    def run(self) -> SuiteRunResult:
        """Run every planned run; raises EvalSuiteError when a budget is set but a model under test has no price."""
        self._check_budget_is_trackable()
        self._spent, self._budget_exceeded, self._budget_untracked = 0.0, False, False
        self._warn_on_self_judging()
        results: list[RunResult] = []
        with self._media_root():
            for cases in self._sandbox_groups():
                results += self._run_group(cases)
        return SuiteRunResult(
            suite=self.loaded.suite.name,
            planned_runs=len(self._plan(self.loaded.cases)),
            runs=results,
            spent_usd=self._spent,
            budget_exceeded=self._budget_exceeded,
            unpriced_models=sorted({model for result in results for model in result.unpriced_models}),
        )

    def _run_group(self, cases: list[EvalCase]) -> list[RunResult]:
        """Run cases sharing a sandbox; if it cannot be set up, their runs are recorded as errored and the suite goes on."""
        results = None
        try:
            with self._target(cases[0]) as target:
                results = self._run_all(CaseRunner(self.loaded, target, self.pricing), self._plan(cases))
        except Exception as e:
            ids = ", ".join(case.id for case in cases)
            logger.warning("Evaluation target for case(s) %s failed", ids, exc_info=True)
            if results is None:
                error = f"Setting up the agent for case(s) {ids} failed: {type(e).__name__}: {e}"
                return [CaseRunner.errored(*planned, error) for planned in self._plan(cases)]
        return results

    def _plan(self, cases: list[EvalCase]) -> list[PlannedRun]:
        suite = self.loaded.suite
        models = suite.models or [None]
        variants = [None, *suite.variants]
        repeats = range(1, suite.repeats + 1)
        return [
            (case, model, variant, repeat) for model, variant, case, repeat in product(models, variants, cases, repeats)
        ]

    def _run_all(self, runner: CaseRunner, plan: list[PlannedRun]) -> list[RunResult]:
        if self.options.parallel == 1:
            results = [self._run_one(runner, planned) for planned in plan]
        else:
            with ThreadPoolExecutor(max_workers=self.options.parallel) as pool:
                results = list(pool.map(lambda planned: self._run_in_thread(runner, planned), plan))
        return [result for result in results if result is not None]

    def _run_in_thread(self, runner: CaseRunner, planned: PlannedRun) -> RunResult | None:
        try:
            return self._run_one(runner, planned)
        finally:
            connection.close()

    def _run_one(self, runner: CaseRunner, planned: PlannedRun) -> RunResult | None:
        budget = self.budget_usd
        with self._lock:
            if budget is not None and (self._spent >= budget or self._budget_untracked):
                self._budget_exceeded = True
                return None
        result = runner.run(*planned)
        with self._lock:
            self._spent += (result.metrics[COST].value or 0) + (result.metrics[JUDGE_COST].value or 0)
            if budget is not None and result.unpriced_models:
                logger.warning(
                    "Unpriced model(s) %s; stopping, as the budget cannot be tracked.", result.unpriced_models
                )
                self._budget_untracked = True
        return result

    def _sandbox_groups(self) -> list[list[EvalCase]]:
        """Cases grouped by the integration data their sandbox is synced from; one group for an existing agent."""
        if not self.loaded.suite.agent.is_sandbox:
            return [self.loaded.cases]
        groups: dict[str, list[EvalCase]] = {}
        for case in self.loaded.cases:
            data = {i.key: i.config.get("data") for i in self.loaded.suite.integrations_for(case)}
            groups.setdefault(json.dumps(data, sort_keys=True, default=str), []).append(case)
        return list(groups.values())

    def _target(self, case: EvalCase) -> BaseAgentTarget:
        suite, user, keep = self.loaded.suite, EvalUser.get(), self.options.keep_conversations
        if not suite.agent.is_sandbox:
            return ExistingAgentTarget(suite.agent.id, user, self.options.allow_real_integrations, keep)
        factory = MockIntegrationFactory(self.loaded.base_dir)
        integrations = [factory.build(config) for config in suite.integrations_for(case)]
        return SandboxAgentTarget(suite.name, suite.agent.type, suite.agent.config, integrations, user, keep)

    def _media_root(self):
        """A temporary MEDIA_ROOT for the run's files, unless conversations, and so their files, are kept."""
        return nullcontext() if self.options.keep_conversations else self._temporary_media_root()

    @staticmethod
    @contextmanager
    def _temporary_media_root() -> Iterator[None]:
        with tempfile.TemporaryDirectory(prefix="eval-media-") as media_root:
            with override_settings(MEDIA_ROOT=media_root):
                yield

    def _check_budget_is_trackable(self) -> None:
        suite = self.loaded.suite
        targets = [*suite.models, *([suite.judge] if suite.judge else [])]
        unpriced = sorted({t.model for t in targets if self.pricing.price_for(t.model) is None})
        if self.budget_usd is not None and unpriced:
            raise EvalSuiteError(
                f"A budget is set but {', '.join(unpriced)} has no price; add 'pricing' to the model in the suite."
            )

    def _suite_prices(self) -> dict:
        targets = [*self.loaded.suite.models, *([self.loaded.suite.judge] if self.loaded.suite.judge else [])]
        return {target.model: target.pricing for target in targets if target.pricing}

    def _warn_on_self_judging(self) -> None:
        judge = self.loaded.suite.judge
        if judge and any(m.provider == judge.provider and m.model == judge.model for m in self.loaded.suite.models):
            logger.warning("The judge %s is also a model under test; it tends to favour its own answers.", judge.model)
