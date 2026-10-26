from enum import StrEnum


class ConversationEnding(StrEnum):
    """How a conversation ended: the user finished or gave up, it hit the case's turn limit, or a turn or the user
    failed."""

    DONE = "done"
    GAVE_UP = "gave_up"
    MAX_TURNS = "max_turns"
    ERROR = "error"
