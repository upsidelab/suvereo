from unittest.mock import MagicMock

import pytest
from langchain_core.messages import AIMessage, HumanMessage
from suvereo_agent_tool_calling import BaseToolCallingAgent
from suvereo_agent_tool_calling.base_tool_calling_agent import EMPTY_ANSWER, REFUSED_ANSWER


class AnsweringAgent(BaseToolCallingAgent):
    __abstract__ = True


def agent() -> AnsweringAgent:
    built = AnsweringAgent.__new__(AnsweringAgent)
    built._injector = MagicMock(memory_compactor=None)
    return built


def record(built: AnsweringAgent, final: AIMessage) -> str:
    return built._record_turn({"messages": [HumanMessage(content="Hi"), final]}, context_messages=[])


class TestFinalAnswer:
    def test_a_normal_answer_is_returned_as_is(self):
        assert record(agent(), AIMessage(content="It's 14:05.")) == "It's 14:05."

    @pytest.mark.parametrize(
        "final",
        [
            AIMessage(content=[], response_metadata={"stop_reason": "refusal"}),
            AIMessage(content="Here is how to", response_metadata={"stop_reason": "refusal"}),
            AIMessage(content="", response_metadata={"finish_reason": "content_filter"}),
            AIMessage(content="", response_metadata={"finish_reason": "SAFETY"}),
            AIMessage(content="", additional_kwargs={"refusal": "I can't assist with that."}),
            AIMessage(content=[{"type": "refusal", "refusal": "I can't assist with that."}]),
        ],
        ids=[
            "anthropic refusal",
            "anthropic refusal after partial text",
            "content filter",
            "gemini safety block",
            "openai refusal",
            "openai responses api refusal",
        ],
    )
    def test_a_refusal_becomes_an_answer_that_says_so(self, final):
        assert record(agent(), final) == REFUSED_ANSWER

    def test_an_empty_answer_asks_to_rephrase(self):
        assert record(agent(), AIMessage(content="")) == EMPTY_ANSWER

    def test_the_history_keeps_the_answer_the_user_got(self):
        built = agent()

        record(built, AIMessage(content=[], response_metadata={"stop_reason": "refusal"}))

        saved = built._injector.chat_history.add_messages.call_args.args[0]
        assert [m.text for m in saved] == ["Hi", REFUSED_ANSWER]

    def test_the_fallback_keeps_the_models_metadata(self):
        built = agent()

        record(built, AIMessage(content="", id="msg_1", response_metadata={"stop_reason": "end_turn"}))

        saved = built._injector.chat_history.add_messages.call_args.args[0][-1]
        assert (saved.id, saved.response_metadata) == ("msg_1", {"stop_reason": "end_turn"})
