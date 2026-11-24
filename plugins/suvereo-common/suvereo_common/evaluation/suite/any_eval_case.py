from typing import Annotated, Any

from pydantic import Discriminator, Tag
from suvereo_common.evaluation.suite.agentic_execution_eval_case import AgenticExecutionEvalCase
from suvereo_common.evaluation.suite.conversation_eval_case import ConversationEvalCase
from suvereo_common.evaluation.suite.suite_kind import SuiteKind

CONVERSATION_FIELDS = ("user_messages", "simulated_user")


def case_kind(case: Any) -> SuiteKind:
    """The kind of case a mapping or case describes: a conversation when it has user messages or a simulated user."""
    if isinstance(case, dict):
        is_conversation = any(field in case for field in CONVERSATION_FIELDS)
    else:
        is_conversation = isinstance(case, ConversationEvalCase)
    return SuiteKind.CONVERSATION if is_conversation else SuiteKind.EXECUTION


#: A case as written in a suite or case file, read as the class its fields describe.
AnyEvalCase = Annotated[
    Annotated[AgenticExecutionEvalCase, Tag(SuiteKind.EXECUTION)]
    | Annotated[ConversationEvalCase, Tag(SuiteKind.CONVERSATION)],
    Discriminator(case_kind),
]
