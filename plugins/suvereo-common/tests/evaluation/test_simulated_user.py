import pytest
from suvereo_common.evaluation.suite import ConversationEvalCase
from suvereo_common.evaluation.trace import Turn
from suvereo_common.evaluation.users import SimulatedUser, StopReason
from suvereo_common.evaluation.users.simulated_user import OPENING, REMINDER

from .metrics.scripted_judge import ScriptedJudge

USER = {"goal": "Find a kettle under 50 EUR", "persona": "terse", "facts": {"budget": "50 EUR"}}


def _user(*replies: str) -> tuple[SimulatedUser, ScriptedJudge]:
    llm = ScriptedJudge(*replies)
    return SimulatedUser(ConversationEvalCase(id="c", simulated_user=USER), llm), llm


class TestSimulatedUser:
    def test_its_goal_persona_and_facts_go_in_the_system_prompt(self):
        user, llm = _user('{"message": "Hi, I need a kettle", "stop": null}')

        assert user.next_message([]).text == "Hi, I need a kettle"
        assert "Your goal: Find a kettle under 50 EUR" in llm.systems[0]
        assert "How you talk: terse" in llm.systems[0]
        assert "- budget: 50 EUR" in llm.systems[0]
        assert [(m.role, m.text) for m in llm.conversations[0]] == [("user", OPENING)]

    def test_the_conversation_is_sent_with_its_own_messages_as_the_assistant_and_the_agent_as_the_user(self):
        user, llm = _user('{"message": "50 EUR", "stop": null}')

        message = user.next_message([Turn(user_message="I need a kettle", answer="## Budget?\nWhat is it?")])

        assert message.text == "50 EUR"
        assert [(m.role, m.text) for m in llm.conversations[0]] == [
            ("user", OPENING),
            ("assistant", '{"message": "I need a kettle", "stop": null}'),
            ("user", "## Budget?\nWhat is it?"),
        ]

    @pytest.mark.parametrize("stop, reason", [("done", StopReason.DONE), ("gave_up", StopReason.GAVE_UP)])
    def test_stops_when_the_goal_is_reached_or_it_gives_up(self, stop, reason):
        user, _ = _user(f'Sure. {{"message": null, "stop": "{stop}"}}')

        assert user.next_message([]).stop_reason is reason

    def test_an_unreadable_reply_is_asked_again_once_with_a_reminder(self):
        user, llm = _user("I'd say hello", '{"message": "Hello", "stop": null}')

        assert user.next_message([]).text == "Hello"
        assert [(m.role, m.text) for m in llm.conversations[1]] == [
            ("user", OPENING),
            ("assistant", "I'd say hello"),
            ("user", REMINDER),
        ]

    @pytest.mark.parametrize("reply", ["no json", '{"message": "", "stop": null}', '{"stop": "max_turns"}'])
    def test_two_unreadable_replies_end_the_run(self, reply):
        user, _ = _user(reply)

        with pytest.raises(ValueError, match="not a message or a stop"):
            user.next_message([])

    def test_needs_a_model(self):
        with pytest.raises(ValueError, match="needs a model"):
            SimulatedUser(ConversationEvalCase(id="c", simulated_user=USER)).next_message([])
