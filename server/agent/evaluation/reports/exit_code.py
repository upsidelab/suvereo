from enum import IntEnum


class ExitCode(IntEnum):
    """What a suite run exits with, so scripts and CI can act on it."""

    PASSED = 0
    BELOW_PASS_THRESHOLD = 1
    INVALID_SUITE = 2
    BUDGET_EXCEEDED = 3
    RUNTIME_ERROR = 4
