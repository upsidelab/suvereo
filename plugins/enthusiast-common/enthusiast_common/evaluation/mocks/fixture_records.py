import csv
import json
from pathlib import Path
from typing import Any

import yaml

from .errors import MockConfigError

READERS = {".yaml": "yaml", ".yml": "yaml", ".json": "json", ".csv": "csv"}


class FixtureRecords:
    """Loads a mock's fixture records: an inline list, or a YAML, JSON or CSV file relative to the suite."""

    @classmethod
    def load(cls, value: Any, base_dir: Path) -> list[dict[str, Any]]:
        """The records as dicts; raises MockConfigError for a missing file, an unknown format or a non-list."""
        if value is None:
            return []
        records = cls._read(base_dir / value) if isinstance(value, (str, Path)) else value
        if not isinstance(records, list) or not all(isinstance(r, dict) for r in records):
            raise MockConfigError(f"Fixture records must be a list of mappings, got {type(records).__name__}.")
        return records

    @staticmethod
    def _read(path: Path) -> Any:
        reader = READERS.get(path.suffix.lower())
        if reader is None:
            raise MockConfigError(f"Cannot read fixture file {path}; use {', '.join(READERS)}.")
        try:
            with path.open(encoding="utf-8-sig", newline="") as f:
                if reader == "csv":
                    return [dict(row) for row in csv.DictReader(f)]
                return yaml.safe_load(f) if reader == "yaml" else json.load(f)
        except (OSError, yaml.YAMLError, json.JSONDecodeError) as e:
            raise MockConfigError(f"Cannot read fixture file {path}: {e}") from e
