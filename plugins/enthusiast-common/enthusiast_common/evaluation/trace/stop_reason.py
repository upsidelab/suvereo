from enum import StrEnum


class StopReason(StrEnum):
    """Why a conversation stopped: the user was done or gave up, which a user simulator says, or the runner hit the
    case's turn limit or an error."""

    DONE = "done"
    GAVE_UP = "gave_up"
    MAX_TURNS = "max_turns"
    ERROR = "error"
