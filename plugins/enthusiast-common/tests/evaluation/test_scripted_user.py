import pytest
from enthusiast_common.evaluation.suite import EvalCase
from enthusiast_common.evaluation.trace import Turn
from enthusiast_common.evaluation.users import ScriptedUser, UserMessage
from pydantic import ValidationError


class TestScriptedUser:
    def test_sends_the_turns_in_order_whatever_the_agent_answers(self):
        user = ScriptedUser(EvalCase(id="c", turns=["Hi", "Under 50 EUR"]))

        first = user.next_message([])
        second = user.next_message([Turn(user_message="Hi", answer="Which kettle?")])

        assert (first.text, second.text) == ("Hi", "Under 50 EUR")
        assert not first.is_stop

    def test_stops_when_the_script_runs_out(self):
        user = ScriptedUser(EvalCase(id="c", turns=["Hi"]))

        message = user.next_message([Turn(user_message="Hi", answer="Hello")])

        assert message.is_stop
        assert message.stop_reason == "done"


class TestUserMessage:
    def test_is_a_message_or_a_stop(self):
        assert not UserMessage.say("Hi").is_stop
        assert UserMessage.stop("gave_up").is_stop

    @pytest.mark.parametrize("fields", [{}, {"text": "Hi", "stop_reason": "done"}, {"text": ""}])
    def test_needs_exactly_one_of_a_message_or_a_stop(self, fields):
        with pytest.raises(ValidationError):
            UserMessage(**fields)
