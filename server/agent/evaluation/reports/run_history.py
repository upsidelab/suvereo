import hashlib
import json
from pathlib import Path
from typing import Any

from agent.evaluation.reports.run_directory import RESULTS_DIR
from agent.evaluation.reports.suite_report import SuiteReport
from agent.evaluation.reports.suite_verdict import SuiteVerdict

HISTORY_FILE = "history.jsonl"


class RunHistory:
    def __init__(self, suite_dir: Path):
        self.path = suite_dir / RESULTS_DIR / HISTORY_FILE

    def record(self, report: SuiteReport, run_dir: Path, note: str = "") -> None:
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
        variant = next((v for v in report.loaded.suite.variants if v.name == variant_name), None)
        if variant is None or variant.system_prompt_file is None:
            return None
        try:
            prompt = (report.loaded.base_dir / variant.system_prompt_file).read_bytes()
        except OSError:
            return None
        return hashlib.sha256(prompt).hexdigest()[:12]
