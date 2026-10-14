import hashlib
import re

from enthusiast_common.evaluation.loaded_suite import LoadedSuite
from enthusiast_common.evaluation.metrics import MetricRegistry
from enthusiast_common.evaluation.metrics.auto import CostUsd
from enthusiast_common.evaluation.suite import EvalCase, Gate, MetricConfig, ReportName

from agent.evaluation.aggregation import PASS_RATE, CandidateMetrics, MetricAggregator
from agent.evaluation.runner import RunResult
from agent.evaluation.runner.run_result import DEFAULT_MODEL
from agent.evaluation.runner.run_scorer import BOOL_GATE
from agent.evaluation.runner.suite_run_result import SuiteRunResult
from agent.evaluation.suite_metric_configs import suite_metric_configs

from .git_state import GitState

UNSAFE_IN_FILE_NAMES = re.compile(r"[^A-Za-z0-9._-]+")


class SuiteReport:
    """What every report writer reads from one suite run, worked out once: the runs with their ids and trace files,
    each candidate's aggregated metrics in comparison order (pass rate, then mean cost), the cases and the metrics,
    and how the run was started (git state, command-line args)."""

    def __init__(
        self,
        loaded: LoadedSuite,
        result: SuiteRunResult,
        reports: list[ReportName] | None = None,
        aggregator: MetricAggregator | None = None,
        git: GitState | None = None,
        args: list[str] | None = None,
    ):
        self.loaded = loaded
        self.result = result
        self.git = git or GitState()
        self.args = args or []
        self.reports: list[ReportName] = loaded.suite.reports if reports is None else reports
        candidates = (aggregator or MetricAggregator.for_suite(loaded)).aggregate_per_candidate(result.runs)
        self.candidates: list[CandidateMetrics] = sorted(candidates, key=self._comparison_order)
        self.cases: list[EvalCase] = loaded.cases
        self.metric_configs: dict[str, MetricConfig] = suite_metric_configs(loaded)
        self._registry = MetricRegistry()

    @property
    def runs(self) -> list[RunResult]:
        return self.result.runs

    def run_id(self, run: RunResult) -> str:
        """A run's id, also its trace file's name: <case>__<model>__<variant>__r<repeat>, safe in file names. When a
        part had characters replaced (e.g. the '/' in openai/gpt-4o), a short hash of the original keeps ids unique."""
        parts = [run.case_id, run.model or DEFAULT_MODEL, run.variant]
        safe_parts = [UNSAFE_IN_FILE_NAMES.sub("-", part) for part in parts]
        run_id = f"{'__'.join(safe_parts)}__r{run.repeat}"
        if safe_parts == parts:
            return run_id
        return f"{run_id}-{hashlib.sha1('/'.join(parts).encode()).hexdigest()[:6]}"

    def trace_path(self, run: RunResult) -> str:
        """Where the traces report writes the run's trace, relative to the run directory."""
        return f"runs/{self.run_id(run)}.json"

    def linked_trace_path(self, run: RunResult) -> str | None:
        """The run's trace file for other reports to link to; None when the traces report isn't selected."""
        return self.trace_path(run) if "traces" in self.reports else None

    def provider_of(self, model_label: str) -> str:
        """The provider of a model under test, by its label; empty for the DataSet's configured model."""
        return next((m.provider for m in self.loaded.suite.models if m.display_label == model_label), "")

    def gate_for(self, case_id: str, metric: str) -> Gate | None:
        """The gate a case's metric was checked against: its own, or equals: true for a bool metric."""
        case = next((c for c in self.cases if c.id == case_id), None)
        config = next((m for m in self.loaded.suite.metrics_for(case) if m.name == metric), None) if case else None
        if config is None or config.gate is not None:
            return config.gate if config else None
        return BOOL_GATE if self._registry.metric_class(config.type).VALUE_TYPE == "bool" else None

    @staticmethod
    def _comparison_order(candidate: CandidateMetrics) -> tuple[float, float]:
        pass_rate = candidate.metrics[PASS_RATE].value or 0.0
        cost = candidate.metrics.get(CostUsd.NAME)
        return -pass_rate, cost.mean if cost and cost.mean is not None else float("inf")
