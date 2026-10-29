from pathlib import Path


class EvalSuiteError(Exception):
    """An evaluation suite that cannot be used as written."""


class CaseSourceError(EvalSuiteError):
    """A case file that cannot be read, located by file and, for CSV, row and column."""

    def __init__(self, path: Path, message: str, row: int | None = None, column: str | None = None):
        self.path = path
        self.message = message
        self.row = row
        self.column = column
        location = str(path)
        if row is not None:
            location += f", row {row}"
        if column is not None:
            location += f", column '{column}'"
        super().__init__(f"{location}: {message}")


class DuplicateCaseError(EvalSuiteError):
    """Two cases share an id, across any of the suite's case sources."""

    def __init__(self, case_id: str, first: str, second: str):
        self.case_id = case_id
        super().__init__(f"Case id '{case_id}' is defined twice: in {first} and in {second}.")
