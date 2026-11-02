import pytest
from suvereo_common.agentic_execution import BaseAgenticExecutionDefinition


class TestExecutionTools:
    def test_tools_default_to_the_agents(self):
        class Execution(BaseAgenticExecutionDefinition):
            def execute(self, input_data, conversation):
                return ""

        assert Execution.TOOLS is None

    def test_a_definition_still_setting_extra_tools_is_rejected(self):
        with pytest.raises(TypeError, match="EXTRA_TOOLS"):

            class LegacyExecution(BaseAgenticExecutionDefinition):
                EXTRA_TOOLS = []

                def execute(self, input_data, conversation):
                    return ""
