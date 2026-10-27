import pytest
from enthusiast_common.evaluation.suite import ConversationEvalCase
from enthusiast_common.evaluation.trace import Turn
from enthusiast_common.evaluation.users import SimulatedUser, StopReason

from .metrics.scripted_judge import ScriptedJudge

USER = {"goal": "Find a kettle under 50 EUR", "persona": "terse", "facts": {"budget": "50 EUR"}}


def _user(*replies: str) -> tuple[SimulatedUser, ScriptedJudge]:
    llm = ScriptedJudge(*replies)
    return SimulatedUser(ConversationEvalCase(id="c", simulated_user=USER), llm), llm


class TestSimulatedUser:
    def test_writes_the_next_message_from_its_goal_persona_facts_and_the_conversation(self):
        user, llm = _user('{"message": "50 EUR", "stop": null}')

        message = user.next_message([Turn(user_message="I need a kettle", answer="## Budget?\nWhat is it?")])

        prompt = llm.prompts[0]
        assert message.text == "50 EUR"
        assert "Your goal: Find a kettle under 50 EUR" in prompt
        assert "How you talk: terse" in prompt
        assert "- budget: 50 EUR" in prompt
        assert "you:\n  I need a kettle\nassistant:\n  ## Budget?\n  What is it?" in prompt

    def test_opens_the_conversation_when_there_are_no_turns(self):
        user, llm = _user('{"message": "Hi, I need a kettle", "stop": null}')

        assert user.next_message([]).text == "Hi, I need a kettle"
        assert "(nothing yet; write the first message)" in llm.prompts[0]

    @pytest.mark.parametrize("stop, reason", [("done", StopReason.DONE), ("gave_up", StopReason.GAVE_UP)])
    def test_stops_when_the_goal_is_reached_or_it_gives_up(self, stop, reason):
        user, _ = _user(f'Sure. {{"message": null, "stop": "{stop}"}}')

        assert user.next_message([]).stop_reason is reason

    def test_an_unreadable_reply_is_asked_again_once(self):
        user, llm = _user("I'd say hello", '{"message": "Hello", "stop": null}')

        assert user.next_message([]).text == "Hello"
        assert len(llm.prompts) == 2

    @pytest.mark.parametrize("reply", ["no json", '{"message": "", "stop": null}', '{"stop": "max_turns"}'])
    def test_two_unreadable_replies_end_the_run(self, reply):
        user, _ = _user(reply)

        with pytest.raises(ValueError, match="not a message or a stop"):
            user.next_message([])

    def test_needs_a_model(self):
        with pytest.raises(ValueError, match="needs a model"):
            SimulatedUser(ConversationEvalCase(id="c", simulated_user=USER)).next_message([])
