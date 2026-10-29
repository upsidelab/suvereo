from suvereo_common.evaluation.loaded_suite import LoadedSuite
from suvereo_common.evaluation.suite import ConversationEvalCase, ModelTarget


def has_simulated_users(loaded: LoadedSuite) -> bool:
    """Whether any case is played by a simulated user, an LLM one or a custom simulator."""
    return any(isinstance(case, ConversationEvalCase) and case.simulated_user for case in loaded.cases)


def has_user_goals(loaded: LoadedSuite) -> bool:
    """Whether any case's simulated user has a goal, which the suite's judge decides was reached or not."""
    return any(
        isinstance(case, ConversationEvalCase) and case.simulated_user and case.simulated_user.goal
        for case in loaded.cases
    )


def user_model_in_use(loaded: LoadedSuite) -> ModelTarget | None:
    """The model simulated users ask, the suite's user_model; none when no case has a simulated user."""
    return loaded.suite.user_model if has_simulated_users(loaded) else None
