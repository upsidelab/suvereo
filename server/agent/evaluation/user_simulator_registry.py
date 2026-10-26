from django.utils.module_loading import import_string
from enthusiast_common.evaluation.errors import EvalSuiteError
from enthusiast_common.evaluation.suite import ConversationEvalCase
from enthusiast_common.evaluation.users import BaseUserSimulator, ScriptedUser


class UserSimulatorRegistry:
    """Finds the user simulator of a conversation case: ScriptedUser for fixed user messages, otherwise the class its
    simulated user names by dotted path."""

    def simulator_for(self, case: ConversationEvalCase) -> BaseUserSimulator:
        """A simulator playing the case's user; raises EvalSuiteError when its class can't be loaded."""
        if case.user_messages:
            return ScriptedUser(case)
        return self.simulator_class(case.simulated_user.class_path)(case)

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
