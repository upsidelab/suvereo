import hashlib
import re

from suvereo_common.evaluation.loaded_suite import LoadedSuite
from suvereo_common.evaluation.metrics import BaseMetric, MetricRegistry
from suvereo_common.evaluation.metrics.auto import GoalReached, Turns
from suvereo_common.evaluation.suite import EvalCase, MetricConfig, PassThreshold, ReportName, SuiteKind

from agent.evaluation.aggregation import PASS_RATE, RATES, CandidateMetrics, MetricAggregator
from agent.evaluation.reports.baseline_diff import BaselineDiff
from agent.evaluation.reports.case_outcome import CaseOutcome
from agent.evaluation.reports.git_state import GitState
from agent.evaluation.reports.summary_file import SummaryFile
from agent.evaluation.resolved_kind import resolved_kind
from agent.evaluation.runner import RunResult
from agent.evaluation.runner.run_result import DEFAULT_MODEL
from agent.evaluation.runner.run_scorer import BOOL_THRESHOLD
from agent.evaluation.runner.suite_run_result import SuiteRunResult
from agent.evaluation.suite_metric_configs import suite_metric_configs

UNSAFE_IN_FILE_NAMES = re.compile(r"[^A-Za-z0-9._-]+")


class SuiteReport:
    def __init__(
        self,
        loaded: LoadedSuite,
        result: SuiteRunResult,
        reports: list[ReportName] | None = None,
        aggregator: MetricAggregator | None = None,
        git: GitState | None = None,
        args: list[str] | None = None,
        baseline: SummaryFile | None = None,
    ):
        self.loaded = loaded
        self.result = result
        self.kind = resolved_kind(loaded.suite)
        self.git = git or GitState()
        self.args = args or []
        self.reports: list[ReportName] = loaded.suite.reports if reports is None else reports
        candidates = (aggregator or MetricAggregator.for_suite(loaded)).aggregate_per_candidate(result.runs)
        self.candidates: list[CandidateMetrics] = sorted(candidates, key=self._comparison_order)
        self.cases: list[EvalCase] = loaded.cases
        self.metric_configs: dict[str, MetricConfig] = suite_metric_configs(loaded)
        self._registry = MetricRegistry()
        self.baseline_diff: BaselineDiff | None = (
            BaselineDiff.between(self.candidates, self.case_outcomes(), list(self.metric_configs), baseline)
            if baseline
            else None
        )

    @property
    def runs(self) -> list[RunResult]:
        return self.result.runs

    @property
    def rates(self) -> tuple[str, ...]:
        return RATES[self.kind]

    @property
    def outcome_figures(self) -> list[str]:
        return [GoalReached.NAME, Turns.NAME] if self.kind == SuiteKind.CONVERSATION else []

    def case_outcomes(self) -> list[CaseOutcome]:
        outcomes = []
        for case in self.cases:
            for candidate in self.candidates:
                runs = [run for run in candidate.runs if run.case_id == case.id]
                if runs:
                    passed = sum(run.passed for run in runs)
                    outcomes.append(
                        CaseOutcome(case_id=case.id, candidate=candidate.candidate, passed_runs=passed, runs=len(runs))
                    )
        return outcomes

    def run_id(self, run: RunResult) -> str:
        parts = [run.case_id, run.model or DEFAULT_MODEL, run.variant]
        safe_parts = [UNSAFE_IN_FILE_NAMES.sub("-", part) for part in parts]
        run_id = f"{'__'.join(safe_parts)}__r{run.repeat}"
        if safe_parts == parts:
            return run_id
        return f"{run_id}-{hashlib.sha1('/'.join(parts).encode()).hexdigest()[:6]}"

    def trace_path(self, run: RunResult) -> str:
        return f"runs/{self.run_id(run)}.json"

    def linked_trace_path(self, run: RunResult) -> str | None:
        return self.trace_path(run) if "traces" in self.reports else None

    def transcript_path(self, run: RunResult) -> str:
        return f"transcripts/{self.run_id(run)}.md"

    def linked_transcript_path(self, run: RunResult) -> str | None:
        return (
            self.transcript_path(run) if self.kind == SuiteKind.CONVERSATION and "transcripts" in self.reports else None
        )

    def provider_of(self, model_label: str) -> str:
        return next((m.provider for m in self.loaded.suite.models if m.display_label == model_label), "")

    def threshold_for(self, case_id: str, metric: str) -> PassThreshold | None:
        case = next((c for c in self.cases if c.id == case_id), None)
        config = next((m for m in self.loaded.suite.metrics_for(case) if m.name == metric), None) if case else None
        if config is None or config.pass_threshold is not None:
            return config.pass_threshold if config else None
        return BOOL_THRESHOLD if self._registry.metric_class(config.type).VALUE_TYPE == "bool" else None

    def metric_class_of(self, metric: str) -> type[BaseMetric]:
        return self._registry.metric_class(self.metric_configs[metric].type)

    @staticmethod
    def _comparison_order(candidate: CandidateMetrics) -> tuple[float, float]:
        pass_rate = candidate.metrics[PASS_RATE].value or 0.0
        cost = candidate.cost_mean_usd
        return -pass_rate, cost if cost is not None else float("inf")
