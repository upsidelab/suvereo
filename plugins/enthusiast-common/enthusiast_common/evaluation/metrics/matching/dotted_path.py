from typing import Any

MISSING = object()


class DottedPath:
    """A path such as ``items.0.sku`` into nested dicts and lists; numeric segments index lists."""

    def __init__(self, path: str):
        self.path = path
        self.segments = [segment for segment in path.split(".") if segment]

    def get(self, value: Any) -> Any:
        """Follow the path from a value.

        Args:
            value: The root to start from.

        Returns:
            The value at the path, or ``MISSING`` when any segment is absent.
        """
        for segment in self.segments:
            if isinstance(value, dict) and segment in value:
                value = value[segment]
            elif isinstance(value, (list, tuple)) and segment.isdigit() and int(segment) < len(value):
                value = value[int(segment)]
            else:
                return MISSING
        return value
