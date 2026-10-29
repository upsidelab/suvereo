from suvereo_common.evaluation.trace import LLMCall, ToolCall, Turn
from suvereo_common.evaluation.users import BaseUserSimulator, StopReason, UserMessage

from agent.evaluation.integrations import EvalIntegrationPluginResolver
from agent.evaluation.run_context import EvalRunContext

from .greeter import GreeterIntegrationPlugin


class FakeChat:
    """Stands in for ConversationManager.get_answer: each turn makes one LLM call; "greet <name>" greets through the
    greeter mock as a tool would, "json" answers with a JSON object and "boom" raises."""

    def __init__(self):
        self.calls: list[tuple] = []

    def __call__(self, conversation, text, **kwargs):
        self.calls.append((conversation, text, kwargs))
        recorder, number = EvalRunContext.current().recorder, len(self.calls)
        recorder.record_llm_call(LLMCall(run_id=f"llm-{number}"))
        if text == "boom":
            raise RuntimeError("model down")
        if text == "json":
            return '{"greeting": "Hi"}'
        if text.startswith("greet "):
            recorder.record_tool_call(ToolCall(run_id=f"tool-{number}", name="greet"))
            return (
                EvalIntegrationPluginResolver().resolve(None, GreeterIntegrationPlugin).build_greeter().greet(text[6:])
            )
        return f"You said: {text}"


class PoliteUser(BaseUserSimulator):
    """Asks to greet the name in its params, says thanks, then stops."""

    def next_message(self, turns: list[Turn]) -> UserMessage:
        messages = [f"greet {self.simulated_user.params['name']}", "thanks"]
        if len(turns) < len(messages):
            return UserMessage.say(messages[len(turns)])
        return UserMessage.stop(StopReason.DONE)


class EndlessUser(BaseUserSimulator):
    """Never stops on its own."""

    def next_message(self, turns: list[Turn]) -> UserMessage:
        return UserMessage.say("more")


class GivingUpUser(BaseUserSimulator):
    """Says hi once, then gives up."""

    def next_message(self, turns: list[Turn]) -> UserMessage:
        return UserMessage.stop(StopReason.GAVE_UP) if turns else UserMessage.say("Hi")


class FailingUser(BaseUserSimulator):
    """Says hi, then fails while writing its second message."""

    def next_message(self, turns: list[Turn]) -> UserMessage:
        if turns:
            raise RuntimeError("simulator broke")
        return UserMessage.say("Hi")


class NotASimulator:
    pass
