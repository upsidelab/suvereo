from textwrap import indent

from ..json_reply import JsonReply
from ..trace import StopReason, Turn
from .base_user_simulator import BaseUserSimulator
from .user_message import USER_STOP_REASONS, UserMessage

ATTEMPTS = 2
PROMPT = """You are role-playing a user chatting with an AI assistant. Stay in character.

Your goal: {goal}
How you talk: {persona}
What you know (answer only from this; if asked anything else, say you don't know; never invent details):
{facts}

Rules:
- Pursue the goal one step at a time, as a real user would; don't state everything at once.
- Answer the assistant's questions from what you know.
- Stop with "done" once the goal is reached, or "gave_up" if the assistant can't help or keeps going in circles.

Reply with JSON only: {{"message": "<your next message>", "stop": null}}
or, to end the conversation: {{"message": null, "stop": "done" | "gave_up"}}

The conversation so far:
{conversation}"""


class SimulatedUser(BaseUserSimulator):
    """An LLM playing the case's simulated user: it chases the goal in the persona's voice, answers only from its
    facts, and stops when the goal is reached or it gives up. A reply it can't read is asked again once."""

    def next_message(self, turns: list[Turn]) -> UserMessage:
        if self.llm is None:
            raise ValueError("The simulated user needs a model; set 'user_model' in the suite.")
        prompt = self._prompt(turns)
        reply = ""
        for _ in range(ATTEMPTS):
            reply = self.llm.complete(prompt)
            message = self._parse(reply)
            if message is not None:
                return message
        raise ValueError(f"The simulated user's reply is not a message or a stop: {reply!r}")

    def _prompt(self, turns: list[Turn]) -> str:
        user = self.simulated_user
        facts = "\n".join(f"- {key}: {value}" for key, value in user.facts.items()) or "- nothing beyond your goal"
        return PROMPT.format(
            goal=user.goal, persona=user.persona or "plainly", facts=facts, conversation=self._conversation(turns)
        )

    @staticmethod
    def _conversation(turns: list[Turn]) -> str:
        lines = []
        for turn in turns:
            lines.append(f"you:\n{indent(turn.user_message, '  ')}")
            lines.append(f"assistant:\n{indent(turn.answer or '(no answer)', '  ')}")
        return "\n".join(lines) or "(nothing yet; write the first message)"

    @staticmethod
    def _parse(reply: str) -> UserMessage | None:
        for value in JsonReply.objects(reply):
            stop, text = value.get("stop"), value.get("message")
            if stop in USER_STOP_REASONS:
                return UserMessage.stop(StopReason(stop))
            if stop is None and isinstance(text, str) and text.strip():
                return UserMessage.say(text)
        return None
