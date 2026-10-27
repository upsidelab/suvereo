import json
import logging
import time

from enthusiast_common.agentic_execution.memory import ToolScratchpad
from enthusiast_common.agents import ConfigType
from enthusiast_common.evaluation.base_model_client import BaseModelClient
from enthusiast_common.evaluation.suite import ConversationEvalCase, EvalCase
from enthusiast_common.evaluation.trace import StopReason, TraceRecorder, Turn
from enthusiast_common.evaluation.users import BaseUserSimulator

from agent.conversation.manager import ConversationManager
from agent.core.agents.config_overrides import AgentConfigOverrides
from agent.evaluation.user_simulator_registry import UserSimulatorRegistry
from agent.models import Conversation

from .base_run_driver import BaseRunDriver

logger = logging.getLogger(__name__)


class ConversationRunDriver(BaseRunDriver):
    """Chats with the agent turn by turn, the case's user simulator writing the user's side, until it stops, the
    case's turn limit is reached or a turn raises; records on the trace why it stopped."""

    def run(
        self,
        case: EvalCase,
        conversation: Conversation,
        overrides: AgentConfigOverrides,
        recorder: TraceRecorder,
        user_llm: BaseModelClient | None = None,
    ) -> None:
        if not isinstance(case, ConversationEvalCase):
            raise TypeError(f"Case '{case.id}' is not a conversation case; this suite runs conversations.")
        trace, scratchpad = recorder.trace, ToolScratchpad()
        try:
            simulator = UserSimulatorRegistry().simulator_for(case, user_llm)
            trace.stop_reason = self._converse(
                simulator, self._max_turns(case), conversation, overrides, scratchpad, recorder
            )
        except Exception:
            trace.stop_reason = StopReason.ERROR
            raise
        finally:
            trace.scratchpad = scratchpad.entries()
            trace.output = self._output(trace.turns)

    def _converse(
        self,
        simulator: BaseUserSimulator,
        max_turns: int | None,
        conversation: Conversation,
        overrides: AgentConfigOverrides,
        scratchpad: ToolScratchpad,
        recorder: TraceRecorder,
    ) -> StopReason:
        trace = recorder.trace
        while max_turns is None or len(trace.turns) < max_turns:
            message = simulator.next_message(trace.turns)
            if message.is_stop:
                return message.stop_reason
            turn = self._take_turn(message.text, conversation, overrides, scratchpad, recorder)
            trace.record_turn(turn)
            if turn.error is not None:
                trace.error = turn.error
                return StopReason.ERROR
        return StopReason.MAX_TURNS

    @staticmethod
    def _max_turns(case: ConversationEvalCase) -> int | None:
        """A simulated user's turn limit; fixed user messages end with the last one."""
        return case.simulated_user.max_turns if case.simulated_user is not None else None

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
        """The last answer given, plus its fields when it is a JSON object, so output metrics can check them."""
        answer = next((turn.answer for turn in reversed(turns) if turn.answer is not None), None)
        if answer is None:
            return None
        try:
            parsed = json.loads(answer)
        except ValueError:
            parsed = None
        return {**parsed, "answer": answer} if isinstance(parsed, dict) else {"answer": answer}
