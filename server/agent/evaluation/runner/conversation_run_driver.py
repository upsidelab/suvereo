import json
import logging
import time

from django.utils.module_loading import import_string
from enthusiast_common.agentic_execution.memory import ToolScratchpad
from enthusiast_common.agents import ConfigType
from enthusiast_common.evaluation.suite import ConversationEvalCase, EvalCase
from enthusiast_common.evaluation.trace import TraceRecorder, Turn
from enthusiast_common.evaluation.users import BaseUserSimulator, ScriptedUser

from agent.conversation.manager import ConversationManager
from agent.core.agents.config_overrides import AgentConfigOverrides
from agent.models import Conversation

from .base_run_driver import BaseRunDriver

logger = logging.getLogger(__name__)


class ConversationRunDriver(BaseRunDriver):
    """Chats with the agent turn by turn, the case's user simulator writing the user's side, until it stops or the
    case's turn limit is reached; a turn that raises ends the conversation with the error."""

    def run(
        self, case: EvalCase, conversation: Conversation, overrides: AgentConfigOverrides, recorder: TraceRecorder
    ) -> None:
        if not isinstance(case, ConversationEvalCase):
            raise TypeError(f"Case '{case.id}' is not a conversation case; this suite runs conversations.")
        simulator, max_turns = self.simulator_for(case), self.max_turns_for(case)
        trace, scratchpad = recorder.trace, ToolScratchpad()
        try:
            while len(trace.turns) < max_turns:
                message = simulator.next_message(trace.turns)
                if message.is_stop:
                    break
                turn = self._take_turn(message.text, conversation, overrides, scratchpad, recorder)
                trace.record_turn(turn)
                if turn.error is not None:
                    trace.error = turn.error
                    break
        finally:
            trace.scratchpad = scratchpad.entries()
            trace.output = self._output(trace.turns)

    @classmethod
    def simulator_for(cls, case: ConversationEvalCase) -> BaseUserSimulator:
        """ScriptedUser for a case with user messages, otherwise the custom simulator its simulated user names."""
        if case.user_messages:
            return ScriptedUser(case)
        return cls.simulator_class(case.simulated_user.class_path)(case)

    @staticmethod
    def simulator_class(path: str) -> type[BaseUserSimulator]:
        """The BaseUserSimulator subclass at a dotted path; raises ImportError or TypeError."""
        simulator_class = import_string(path)
        if not (isinstance(simulator_class, type) and issubclass(simulator_class, BaseUserSimulator)):
            raise TypeError(f"{path} is not a BaseUserSimulator.")
        return simulator_class

    @staticmethod
    def max_turns_for(case: ConversationEvalCase) -> int:
        return len(case.user_messages) if case.user_messages else case.simulated_user.max_turns

    @staticmethod
    def _take_turn(
        text: str,
        conversation: Conversation,
        overrides: AgentConfigOverrides,
        scratchpad: ToolScratchpad,
        recorder: TraceRecorder,
    ) -> Turn:
        trace = recorder.trace
        llm_calls_before, tool_calls_before = len(trace.llm_calls), len(trace.tool_calls)
        started = time.perf_counter()
        answer, error = None, None
        try:
            answer = ConversationManager().get_answer(
                conversation,
                text,
                streaming=False,
                config_type=ConfigType.CONVERSATION,
                tool_scratchpad=scratchpad,
                overrides=overrides,
            )
        except Exception as e:
            logger.warning("Evaluation conversation turn raised", exc_info=True)
            error = f"{type(e).__name__}: {e}"
        return Turn(
            user_message=text,
            answer=answer,
            error=error,
            duration_s=time.perf_counter() - started,
            llm_call_run_ids=[c.run_id for c in trace.llm_calls[llm_calls_before:]],
            tool_call_run_ids=[c.run_id for c in trace.tool_calls[tool_calls_before:]],
        )

    @staticmethod
    def _output(turns: list[Turn]) -> dict | None:
        """The last answer, plus its fields when it is a JSON object, so output metrics can check them."""
        answer = turns[-1].answer if turns else None
        if answer is None:
            return None
        try:
            parsed = json.loads(answer)
        except ValueError:
            parsed = None
        return {**parsed, "answer": answer} if isinstance(parsed, dict) else {"answer": answer}
