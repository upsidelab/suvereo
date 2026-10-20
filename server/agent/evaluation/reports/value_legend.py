from enthusiast_common.evaluation.suite import PassThreshold

from agent.evaluation.aggregation.metric_aggregate import DEFAULT_AGGREGATE_NAMES

from .suite_report import SuiteReport
from .threshold_text import threshold_words

AGGREGATE_WORDS = {
    "mean": "avg",
    "rate": "% of runs",
    "sum": "total",
    "min": "lowest",
    "max": "highest",
    "p50": "median",
    "p95": "p95",
    "distribution": "label counts",
    "most_common": "most common label",
}
FAILURE_FIELDS = {
    "missed": "a pass threshold the run missed: its value, then what passing needs",
    "calls": "mock calls made",
    "expected_calls": "mock calls expected",
    "missing": "expected, not sent",
    "extra": "sent, not expected",
    "mismatched": "fields with a wrong value",
    "expected": "what the case expects",
    "actual": "what the run produced",
    "called": "tools in call order",
    "errors": "schema errors",
    "reason": "why it wasn't measured",
    "error": "what stopped the run",
    "says": "judge score per criterion (success or failure, or 0–1 on a scale) and why",
    "trace": "the run's every LLM, tool and mock call, as JSON",
}


class ValueLegend:
    """Short small-print legends for report.md, under the table or list they explain."""

    @classmethod
    def comparison_note(cls, report: SuiteReport) -> str:
        """One short line per comparison column."""
        return cls._legend(
            [
                ("Candidate", "model/prompt; default = the agent's own prompt"),
                ("Runs", "cases × repeats"),
                ("Pass rate", cls._pass_rate_words(report.loaded.suite.min_pass_rate)),
                ("Flaky", "cases whose repeats disagreed"),
                *((name, cls._metric_words(report, name)) for name in report.metric_configs),
                ("Cost / run", "avg agent LLM cost, judge excluded"),
                ("p95 time (s)", "95% of runs finished within"),
            ]
        )

    @classmethod
    def failures_note(cls, failure_fields: list[str]) -> str:
        """One short line per field the failed runs list; empty when they list none."""
        used = {"says" if field.endswith(" says") else field: field for field in failure_fields}
        used |= {"missed": "❌ metric"} if "missed" in used else {}
        return cls._legend([(used[key], meaning) for key, meaning in FAILURE_FIELDS.items() if key in used])

    @staticmethod
    def _pass_rate_words(min_pass_rate: float | None) -> str:
        needs = f"; needs {min_pass_rate:.0%}" if min_pass_rate is not None else ""
        return f"runs meeting every pass threshold{needs}"

    @staticmethod
    def _legend(lines: list[tuple[str, str]]) -> str:
        return "<br>\n".join(f"<small>**{name}**: {meaning}</small>" for name, meaning in lines)

    @staticmethod
    def _metric_words(report: SuiteReport, name: str) -> str:
        """e.g. 'right items and quantities sent · avg · pass ≥ 0.95'."""
        config = report.metric_configs[name]
        metric_class = report.metric_class_of(name)
        what = config.description or " ".join((metric_class.__doc__ or "").split()).split(". ")[0].split("; ")[0]
        aggregate = config.aggregate or DEFAULT_AGGREGATE_NAMES[metric_class.VALUE_TYPE]
        threshold = config.pass_threshold or (PassThreshold(equals=True) if metric_class.VALUE_TYPE == "bool" else None)
        if threshold is None:
            decides = "info only"
        elif config.required:
            decides = f"pass: {threshold_words(threshold)}"
        else:
            decides = f"warn unless {threshold_words(threshold)}"
        return " · ".join([what.rstrip("."), AGGREGATE_WORDS.get(aggregate, aggregate), decides])
