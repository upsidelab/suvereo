from typing import Any

from ..matching import DottedPath


class ExpectedValues:
    """Where correctness metrics find expected values in a case: ``expected.output.*`` and ``expected.mock_calls.*``."""

    @staticmethod
    def output(expected: dict[str, Any], path: str) -> Any:
        """The expected output value at a path, or ``MISSING``."""
        return DottedPath(f"output.{path}" if path else "output").get(expected)

    @staticmethod
    def mock_calls(expected: dict[str, Any], method: str) -> Any:
        """The expected calls to a mock method, or ``MISSING``."""
        return DottedPath(f"mock_calls.{method}").get(expected)
