class SummaryTruncatedError(Exception):
    """The LLM cut the summary off at its own output token limit."""


class SummaryTooLongError(Exception):
    """The summary still exceeds its size limit after all shortening attempts."""


class EmptySummaryError(Exception):
    """The LLM returned no summary text."""
