from enum import StrEnum


class SuiteKind(StrEnum):
    """How a suite drives its agent: one agentic execution per case, or a conversation of user messages."""

    EXECUTION = "execution"
    CONVERSATION = "conversation"
