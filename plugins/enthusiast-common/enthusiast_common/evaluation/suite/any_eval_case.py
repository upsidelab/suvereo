from typing import Annotated, Any

from pydantic import Discriminator, Tag

from .agentic_execution_eval_case import AgenticExecutionEvalCase
from .conversation_eval_case import ConversationEvalCase
from .suite_kind import SuiteKind

CONVERSATION_FIELDS = ("user_messages", "simulated_user")


def case_kind(case: Any) -> SuiteKind:
    """The kind of case a mapping or case describes: a conversation when it has user messages or a simulated user."""
    if isinstance(case, dict):
        return "conversation" if any(field in case for field in CONVERSATION_FIELDS) else "execution"
    return "conversation" if isinstance(case, ConversationEvalCase) else "execution"


#: A case as written in a suite or case file, read as the class its fields describe.
AnyEvalCase = Annotated[
    Annotated[AgenticExecutionEvalCase, Tag("execution")] | Annotated[ConversationEvalCase, Tag("conversation")],
    Discriminator(case_kind),
]
