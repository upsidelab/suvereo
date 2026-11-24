from suvereo_common.evaluation.loaded_suite import LoadedSuite
from suvereo_common.evaluation.suite import ConversationEvalCase, ModelTarget


def has_simulated_users(loaded: LoadedSuite) -> bool:
    return any(isinstance(case, ConversationEvalCase) and case.simulated_user for case in loaded.cases)


def has_user_goals(loaded: LoadedSuite) -> bool:
    return any(
        isinstance(case, ConversationEvalCase) and case.simulated_user and case.simulated_user.goal
        for case in loaded.cases
    )


def user_model_in_use(loaded: LoadedSuite) -> ModelTarget | None:
    return loaded.suite.user_model if has_simulated_users(loaded) else None
