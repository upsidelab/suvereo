import json

from ..chat_message import ChatMessage
from ..json_reply import JsonReply
from ..trace import StopReason, Turn
from .base_user_simulator import BaseUserSimulator
from .user_message import USER_STOP_REASONS, UserMessage

ATTEMPTS = 2
SYSTEM = """You are role-playing a user chatting with an AI assistant, whose answers reach you as the other side of
this chat. Stay in character.

Your goal: {goal}
How you talk: {persona}
What you know (answer only from this; if asked anything else, say you don't know; never invent details):
{facts}

Rules:
- Open with a short request in a few words, as a real user would; give a fact only when the assistant asks for it.
- Answer the assistant's questions from what you know.
- Want only what your goal and facts say; add no needs or questions of your own.
- Offered several options, pick the one your facts point to or ask which one fits.
- The assistant only answers in this chat; a goal to buy or get something is met once you know which one and what
  your goal asks about it.
- Stop with "done" as soon as the answers have met every part of your goal, or "gave_up" if the assistant can't
  help or keeps going in circles.

Reply with JSON only: {{"message": "<your next message>", "stop": null}}
or, to end the conversation: {{"message": null, "stop": "done" | "gave_up"}}"""
#: Opens the chat, so the user model writes the first message.
OPENING = "(The assistant is waiting for your first message.)"
#: Sent after a reply that isn't the JSON asked for, before asking again.
REMINDER = "Reply with JSON only, as the system prompt says."


class SimulatedUser(BaseUserSimulator):
    """An LLM playing the case's simulated user: it chases the goal in the persona's voice, answers only from its
    facts, and stops when the goal is reached or it gives up. A reply it can't read is asked again once, with a
    reminder of the format."""

    def next_message(self, turns: list[Turn]) -> UserMessage:
        if self.llm is None:
            raise ValueError("The simulated user needs a model; set 'user_model' in the suite.")
        system, messages = self._system(), self._messages(turns)
        reply = ""
        for _ in range(ATTEMPTS):
            reply = self.llm.chat(messages, system)
            message = self._parse(reply)
            if message is not None:
                return message
            messages = [
                *messages,
                ChatMessage(role="assistant", text=reply or "(empty)"),
                ChatMessage(role="user", text=REMINDER),
            ]
        raise ValueError(f"The simulated user's reply is not a message or a stop: {reply!r}")

    def _system(self) -> str:
        user = self.simulated_user
        facts = "\n".join(f"- {key}: {value}" for key, value in user.facts.items()) or "- nothing beyond your goal"
        return SYSTEM.format(goal=user.goal, persona=user.persona or "plainly", facts=facts)

    @staticmethod
    def _messages(turns: list[Turn]) -> list[ChatMessage]:
        """The conversation from the user model's side: its own messages as it wrote them, the agent's answers as the
        other side's."""
        messages = [ChatMessage(role="user", text=OPENING)]
        for turn in turns:
            own = json.dumps({"message": turn.user_message, "stop": None}, ensure_ascii=False)
            messages.append(ChatMessage(role="assistant", text=own))
            messages.append(ChatMessage(role="user", text=turn.answer or "(no answer)"))
        return messages

    @staticmethod
    def _parse(reply: str) -> UserMessage | None:
        for value in JsonReply.objects(reply):
            stop, text = value.get("stop"), value.get("message")
            if stop in USER_STOP_REASONS:
                return UserMessage.stop(StopReason(stop))
            if stop is None and isinstance(text, str) and text.strip():
                return UserMessage.say(text)
        return None
