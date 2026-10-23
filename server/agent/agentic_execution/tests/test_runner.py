from unittest.mock import MagicMock, patch

import pytest
from enthusiast_agent_tools import StopExecutionTool
from enthusiast_common.agentic_execution import BaseAgenticExecutionDefinition, ExecutionInputType
from enthusiast_common.config import LLMToolConfig
from pydantic import ValidationError

from agent.agentic_execution.conversation import ExecutionConversation
from agent.agentic_execution.registry import AgenticExecutionDefinitionRegistry
from agent.agentic_execution.runner import AgenticExecutionRunner
from agent.core.agents.config_overrides import AgentConfigOverrides


class EchoInput(ExecutionInputType):
    text: str


class EchoExecution(BaseAgenticExecutionDefinition):
    EXECUTION_KEY = "echo"
    AGENT_KEY = "echo-agent"
    NAME = "Echo"
    INPUT_TYPE = EchoInput
    VALIDATORS = []

    def execute(self, input_data, conversation):
        return conversation.ask(input_data.text)


@pytest.fixture
def registered():
    with patch.object(AgenticExecutionDefinitionRegistry, "get_by_key", return_value=EchoExecution) as mock:
        yield mock


class TestAgenticExecutionRunner:
    def test_run_drives_the_registered_definition(self, registered):
        conversation = MagicMock()
        conversation.ask.return_value = '{"echo": "hi"}'

        result = AgenticExecutionRunner().run("echo", {"text": "hi"}, conversation)

        registered.assert_called_once_with("echo")
        conversation.ask.assert_called_once_with("hi")
        assert result.success
        assert result.output == {"echo": "hi"}

    def test_run_validates_the_input_against_the_definition(self, registered):
        with pytest.raises(ValidationError):
            AgenticExecutionRunner().run("echo", {}, MagicMock())


class TestExecutionConversation:
    def test_ask_passes_the_overrides_to_the_agent(self):
        overrides = AgentConfigOverrides(system_prompt="variant")

        with patch("agent.agentic_execution.conversation.ConversationManager.get_answer") as get_answer:
            ExecutionConversation(MagicMock(), EchoExecution, overrides).ask("hello")

        assert get_answer.call_args.kwargs["overrides"].system_prompt == "variant"

    def test_ask_without_settings_builds_the_agent_as_configured(self):
        with patch("agent.agentic_execution.conversation.ConversationManager.get_answer") as get_answer:
            ExecutionConversation(MagicMock(), EchoExecution).ask("hello")

        assert get_answer.call_args.kwargs["overrides"] == AgentConfigOverrides()

    def test_ask_builds_the_agent_with_the_definitions_prompt_and_extra_tools(self):
        stop_tool = LLMToolConfig(tool_class=StopExecutionTool)

        class PromptedExecution(EchoExecution):
            SYSTEM_PROMPT = "execution prompt"
            EXTRA_TOOLS = [stop_tool]

        with patch("agent.agentic_execution.conversation.ConversationManager.get_answer") as get_answer:
            ExecutionConversation(MagicMock(), PromptedExecution).ask("hello")

        overrides = get_answer.call_args.kwargs["overrides"]
        assert overrides.system_prompt == "execution prompt"
        assert overrides.extra_tools == [stop_tool]

    def test_given_overrides_win_over_the_definition(self):
        class PromptedExecution(EchoExecution):
            SYSTEM_PROMPT = "execution prompt"

        with patch("agent.agentic_execution.conversation.ConversationManager.get_answer") as get_answer:
            ExecutionConversation(
                MagicMock(), PromptedExecution, AgentConfigOverrides(system_prompt="variant")
            ).ask("hello")

        assert get_answer.call_args.kwargs["overrides"].system_prompt == "variant"

    def test_the_attempt_observer_hears_each_attempt_and_its_errors_never_fail_the_run(self, registered):
        conversation = MagicMock()
        conversation.ask.return_value = '{"echo": "hi"}'
        observer = MagicMock(side_effect=RuntimeError("recording broke"))

        result = AgenticExecutionRunner().run("echo", {"text": "hi"}, conversation, observer)

        observer.assert_called_once_with(1, '{"echo": "hi"}', None)
        assert result.success
