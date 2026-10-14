import csv
from pathlib import Path
from typing import Any, Iterable


class CsvTable:
    """Writes the evaluation CSVs one way: UTF-8 with a BOM (so spreadsheets open them cleanly), commas, RFC 4180
    quoting, bools as true/false, lists joined with ';' and missing values as empty cells."""

    @classmethod
    def write(cls, path: Path, header: list[str], rows: Iterable[list[Any]]) -> Path:
        with path.open("w", encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(header)
            writer.writerows([cls.cell(value) for value in row] for row in rows)
        return path

    @classmethod
    def cell(cls, value: Any) -> str:
        """One value as CSV text."""
        if value is None:
            return ""
        if isinstance(value, bool):
            return "true" if value else "false"
        if isinstance(value, (list, tuple)):
            return ";".join(cls.cell(item) for item in value)
        return str(value)
