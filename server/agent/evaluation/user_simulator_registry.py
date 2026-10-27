from django.utils.module_loading import import_string
from enthusiast_common.evaluation.base_model_client import BaseModelClient
from enthusiast_common.evaluation.errors import EvalSuiteError
from enthusiast_common.evaluation.suite import ConversationEvalCase
from enthusiast_common.evaluation.users import BaseUserSimulator, ScriptedUser, SimulatedUser


class UserSimulatorRegistry:
    """Finds the user simulator of a conversation case: ScriptedUser for fixed user messages, the class a simulated
    user names by dotted path, or else SimulatedUser, an LLM playing it."""

    def simulator_for(self, case: ConversationEvalCase, llm: BaseModelClient | None = None) -> BaseUserSimulator:
        """A simulator playing the case's user, given the suite's user model; raises EvalSuiteError when its class
        can't be loaded."""
        if case.user_messages:
            return ScriptedUser(case)
        if case.simulated_user.class_path is not None:
            return self.simulator_class(case.simulated_user.class_path)(case, llm)
        return SimulatedUser(case, llm)

    @staticmethod
    def simulator_class(path: str) -> type[BaseUserSimulator]:
        """The BaseUserSimulator subclass at a dotted path; raises EvalSuiteError."""
        try:
            simulator_class = import_string(path)
        except ImportError as e:
            raise EvalSuiteError(f"Cannot import {path}: {e}") from e
        if not (isinstance(simulator_class, type) and issubclass(simulator_class, BaseUserSimulator)):
            raise EvalSuiteError(f"{path} is not a BaseUserSimulator.")
        return simulator_class
