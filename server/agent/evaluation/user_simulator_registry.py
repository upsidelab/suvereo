from django.utils.module_loading import import_string
from suvereo_common.evaluation.base_model_client import BaseModelClient
from suvereo_common.evaluation.errors import EvalSuiteError
from suvereo_common.evaluation.suite import ConversationEvalCase
from suvereo_common.evaluation.users import BaseUserSimulator, ScriptedUser, SimulatedUser


class UserSimulatorRegistry:
    def simulator_for(self, case: ConversationEvalCase, llm: BaseModelClient | None = None) -> BaseUserSimulator:
        if case.user_messages:
            return ScriptedUser(case)
        if case.simulated_user.class_path is not None:
            return self.simulator_class(case.simulated_user.class_path)(case, llm)
        return SimulatedUser(case, llm)

    @staticmethod
    def simulator_class(path: str) -> type[BaseUserSimulator]:
        try:
            simulator_class = import_string(path)
        except ImportError as e:
            raise EvalSuiteError(f"Cannot import {path}: {e}") from e
        if not (isinstance(simulator_class, type) and issubclass(simulator_class, BaseUserSimulator)):
            raise EvalSuiteError(f"{path} is not a BaseUserSimulator.")
        return simulator_class
