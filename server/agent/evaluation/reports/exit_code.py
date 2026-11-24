from enum import IntEnum


class ExitCode(IntEnum):
    PASSED = 0
    BELOW_MIN_PASS_RATE = 1
    INVALID_SUITE = 2
    BUDGET_EXCEEDED = 3
    RUNTIME_ERROR = 4
