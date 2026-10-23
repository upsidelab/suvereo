from enthusiast_common.evaluation.suite import EvalCase
from enthusiast_common.evaluation.trace import Turn
from enthusiast_common.evaluation.users import ScriptedUser


class TestScriptedUser:
    def test_sends_the_turns_in_order_whatever_the_agent_answers(self):
        user = ScriptedUser(None, EvalCase(id="c", turns=["Hi", "Under 50 EUR"]))

        first = user.next_message([])
        second = user.next_message([Turn(user_message="Hi", answer="Which kettle?")])

        assert (first.text, second.text) == ("Hi", "Under 50 EUR")
        assert not first.is_stop

    def test_stops_when_the_script_runs_out(self):
        user = ScriptedUser(None, EvalCase(id="c", turns=["Hi"]))

        message = user.next_message([Turn(user_message="Hi", answer="Hello")])

        assert message.is_stop
        assert message.stop_reason == "done"
