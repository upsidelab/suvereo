from unittest.mock import MagicMock

from enthusiast_common.agents import BaseAgent
from enthusiast_common.utils import RequiredFieldsModel
from pydantic import Field


class PromptInput(RequiredFieldsModel):
    tone_of_voice: str = Field(title="Tone of voice", description="How the agent sounds", default="friendly")
    target_language: str = Field(title="Target language", description="Language of answers", default="English")


class StubAgent(BaseAgent):
    AGENT_KEY = "stub"
    NAME = "Stub"
    AGENT_ARGS = None
    PROMPT_INPUT = PromptInput

    def get_answer(self, input_text: str) -> str:
        return input_text

    async def aget_answer(self, input_text: str) -> str:
        return input_text


class RenamingAgent(StubAgent):
    def _get_system_prompt_variables(self) -> dict:
        return {**super()._get_system_prompt_variables(), "language": self.PROMPT_INPUT.target_language}


def build(agent_class: type[BaseAgent], system_prompt: str, prompt_input=None) -> BaseAgent:
    agent = agent_class(
        tools=[], llm=MagicMock(), system_prompt=system_prompt, conversation_id=1, injector=MagicMock(),
        conversation_history_token_limit=10_000
    )
    if prompt_input is not None:
        agent.PROMPT_INPUT = prompt_input
    return agent


class TestSystemPrompt:
    def test_prompt_input_fields_are_available_as_variables(self):
        agent = build(StubAgent, "Sound {tone_of_voice} in {target_language}.", PromptInput(tone_of_voice="formal"))

        assert agent._get_system_prompt() == "Sound formal in English."

    def test_static_prompt_needs_no_prompt_input(self):
        agent = build(StubAgent, "Be helpful.")

        assert agent._get_system_prompt() == "Be helpful."

    def test_override_can_extend_the_defaults(self):
        agent = build(RenamingAgent, "{tone_of_voice}, {language}", PromptInput(target_language="Polish"))

        assert agent._get_system_prompt() == "friendly, Polish"
