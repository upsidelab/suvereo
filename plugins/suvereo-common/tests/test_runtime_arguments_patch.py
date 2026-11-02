from unittest.mock import MagicMock

from suvereo_common.builder import AgentBuilder
from suvereo_common.utils import deep_merge


class TestDeepMerge:
    def test_nested_dicts_are_merged(self):
        assert deep_merge({"a": {"x": 1, "y": 2}}, {"a": {"y": 3}}) == {"a": {"x": 1, "y": 3}}

    def test_other_values_are_replaced(self):
        assert deep_merge({"tools": [1, 2], "a": {"x": 1}}, {"tools": [3], "a": "flat"}) == {"tools": [3], "a": "flat"}

    def test_neither_input_is_modified(self):
        base, patch = {"a": {"x": 1}}, {"a": {"y": 2}}

        deep_merge(base, patch)

        assert base == {"a": {"x": 1}} and patch == {"a": {"y": 2}}


def _builder(stored: dict, patch: dict | None) -> AgentBuilder:
    config = MagicMock()
    config.runtime_arguments_patch = patch
    builder = AgentBuilder(agent_class=MagicMock(), config=config, conversation_id=1)
    builder._repositories = MagicMock()
    builder._repositories.agent.get_agent_configuration_by_id.return_value = stored
    return builder


class TestAgentRuntimeArguments:
    def test_stored_arguments_are_used_as_they_are_without_a_patch(self):
        stored = {"prompt_input": {"tone": "casual"}, "tools": {}}

        assert _builder(stored, None)._agent_runtime_arguments() == stored

    def test_the_patch_is_merged_over_the_stored_arguments(self):
        stored = {"prompt_input": {"tone": "casual", "language": "en"}, "tools": {}}

        arguments = _builder(stored, {"prompt_input": {"tone": "formal"}})._agent_runtime_arguments()

        assert arguments == {"prompt_input": {"tone": "formal", "language": "en"}, "tools": {}}
        assert stored["prompt_input"]["tone"] == "casual"
