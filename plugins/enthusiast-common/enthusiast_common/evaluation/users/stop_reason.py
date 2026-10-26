from enum import StrEnum


class StopReason(StrEnum):
    """Why a simulated user stopped: it got what it wanted, or gave up."""

    DONE = "done"
    GAVE_UP = "gave_up"
