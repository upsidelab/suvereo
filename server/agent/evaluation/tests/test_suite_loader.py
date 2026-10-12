from unittest.mock import patch

import pytest
import yaml
from enthusiast_common.evaluation.errors import EvalSuiteError

from agent.agentic_execution.registry import AgenticExecutionDefinitionRegistry
from agent.evaluation.suite_loader import SuiteLoader

from .greeter import GreeterMockIntegration, GreetingExecution

pytestmark = pytest.mark.django_db

GREETER = f"{GreeterMockIntegration.__module__}.GreeterMockIntegration"


@pytest.fixture(autouse=True)
def _registered():
    with patch.object(AgenticExecutionDefinitionRegistry, "get_all", return_value=[GreetingExecution]):
        yield


def _load(tmp_path, **changes):
    suite = {
        "agent": {"type": "greeter-agent"},
        "models": [{"provider": "OpenAI", "model": "gpt-4o"}],
        "integrations": [{"class": GREETER, "config": {"behaviour": {"greet": {"returns": "Hi"}}}}],
        "metrics": [{"type": "mock_called", "params": {"method": "greet"}}],
        "cases": [{"id": "ada", "input": {"name": "Ada"}}],
        **changes,
    }
    path = tmp_path / "suite.yaml"
    path.write_text(yaml.safe_dump(suite))
    return SuiteLoader().load(path)


class TestSuiteLoader:
    def test_resolves_the_agent_types_only_execution(self, tmp_path):
        loaded = _load(tmp_path)

        assert loaded.suite.execution_key == "greeting"
        assert [case.id for case in loaded.cases] == ["ada"]

    @pytest.mark.parametrize(
        "changes, message",
        [
            ({"agent": {"type": "unknown-agent"}}, "has 0 registered executions"),
            ({"agent": {"id": 999}}, "no agent with id 999"),
            ({"execution_key": "farewell"}, "no execution 'farewell'"),
            ({"models": [{"provider": "Nope", "model": "x"}]}, "Unknown language model provider 'Nope'"),
            ({"variants": [{"name": "v2", "system_prompt_file": "v2.txt"}]}, "no prompt file v2.txt"),
            ({"metrics": [{"type": "no_such_metric"}]}, "Unknown metric 'no_such_metric'"),
            ({"metrics": [{"type": "mock_called", "name": "cost_usd", "params": {"method": "greet"}}]}, "every run"),
            (
                {"integrations": [{"class": GREETER, "config": {"behaviour": {"wave": {"returns": "Hi"}}}}]},
                "no method named wave",
            ),
            ({"cases": [{"id": "ada", "input": {"nickname": "Ada"}}]}, "Case 'ada': invalid input"),
        ],
    )
    def test_fails_early_on_a_suite_the_host_cannot_run(self, tmp_path, changes, message):
        with pytest.raises(EvalSuiteError, match=message):
            _load(tmp_path, **changes)
