import json
import os
from pathlib import Path

import pytest
from django.test import override_settings

from .test_eval_commands import _run_command

QUICKSTART = Path(__file__).resolve().parents[4] / "domain_plugins/enthusiast-agent-order-intake/evals/quickstart"


@pytest.mark.llm
@pytest.mark.django_db(transaction=True)
@override_settings(
    AVAILABLE_AGENTS=["enthusiast_agent_order_intake.OrderIntakeAgent"],
    AVAILABLE_AGENTIC_EXECUTION_DEFINITIONS=["enthusiast_agent_order_intake.OrderIntakeAgenticExecutionDefinition"],
)
def test_the_quickstart_suite_runs_end_to_end_against_a_real_llm():
    if not os.environ.get("OPENAI_API_KEY"):
        pytest.skip("OPENAI_API_KEY is not set")

    code, out, err = _run_command("runeval", str(QUICKSTART / "suite.yaml"), "--format", "json", "--budget", "0.10")

    summary = json.loads(out)
    assert code in (0, 1), err
    assert summary["status"] == "complete"
    assert len(summary["cases"]) == 3
    assert {"report.md", "results.csv", "comparison.csv", "cases.csv", "metrics.csv", "runs"} <= {
        p.name for p in (QUICKSTART / "results" / "latest").iterdir()
    }
