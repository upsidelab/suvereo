from enthusiast_vertical_common.errors import RetrieverError


class RetrieverSQLExecutionError(RetrieverError):
    def __init__(self, error: Exception):
        super().__init__(error)
        self._error = error

    @property
    def agent_friendly_message(self) -> str:
        return f"The SQL query failed with the following error {self._error}. Fix it and try again."
