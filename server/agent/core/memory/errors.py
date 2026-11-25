class SummaryTruncatedError(Exception):
    """The LLM cut the summary off at its output token cap."""


class SummaryTooLongError(Exception):
    """The summary still exceeds its size limit after all shortening attempts."""
