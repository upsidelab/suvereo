class RetrieverSQLPermissionError(Exception):
    """Raised when an agent-generated SQL query touches tables/constructs it is not allowed to."""


class RetrieverSQLExecutionError(Exception):
    """Raised when an agent-generated SQL query fails to execute."""
