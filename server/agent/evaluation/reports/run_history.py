import hashlib
import json
from pathlib import Path
from typing import Any

from .run_directory import RESULTS_DIR
from .suite_report import SuiteReport
from .suite_verdict import SuiteVerdict

HISTORY_FILE = "history.jsonl"


class RunHistory:
    """<suite_dir>/results/history.jsonl: one line per candidate of every run, so progress across iterations (e.g. a
    coding agent trying prompt changes) shows at a glance; it sits with the runs, out of git."""

    def __init__(self, suite_dir: Path):
        self.path = suite_dir / RESULTS_DIR / HISTORY_FILE

    def record(self, report: SuiteReport, run_dir: Path, note: str = "") -> None:
        """Append a line per candidate of the run in run_dir."""
        verdict = SuiteVerdict.of(report)
        shared = {
            "run": run_dir.name,
            "finished_at": report.result.finished_at,
            "git_sha": report.git.sha,
            "git_dirty": report.git.dirty,
            "status": verdict.status,
            "exit_code": int(verdict.exit_code),
            "spent_usd": report.result.spent_usd,
            "note": note,
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as history:
            for c in report.candidates:
                line = {
                    **shared,
                    "candidate": c.candidate,
                    "prompt_hash": self._prompt_hash(report, c.variant),
                    "runs": len(c.runs),
                    **{name: c.metrics[name].value for name in report.rates},
                    "cost_mean_usd": c.cost_mean_usd,
                }
                history.write(json.dumps(line, default=str) + "\n")

    def entries(self) -> list[dict[str, Any]]:
        """Every recorded line, oldest first; skips lines that aren't JSON (e.g. from an interrupted write)."""
        if not self.path.is_file():
            return []
        entries = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return entries

    @staticmethod
    def _prompt_hash(report: SuiteReport, variant_name: str) -> str | None:
        """A short hash of the variant's prompt file, so edits to it tell apart runs of the same variant."""
        variant = next((v for v in report.loaded.suite.variants if v.name == variant_name), None)
        if variant is None or variant.system_prompt_file is None:
            return None
        try:
            prompt = (report.loaded.base_dir / variant.system_prompt_file).read_bytes()
        except OSError:
            return None
        return hashlib.sha256(prompt).hexdigest()[:12]
