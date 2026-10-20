import csv
import json
from typing import Any

from ..errors import CaseSourceError
from ..suite import EvalCase
from .base import BaseCaseSource

LIST_SEPARATOR = ";"
DOTTED_PREFIXES = ("input", "expected")
PLAIN_COLUMNS = ("id", "description")
LIST_COLUMNS = ("tags", "files")
JSON_STARTS = ("[", "{", '"')


class CsvCaseSource(BaseCaseSource):
    """A CSV file with one case per row; only cells starting with '[', '{' or '"' are parsed as JSON."""

    def load(self) -> list[EvalCase]:
        try:
            with self.path.open(encoding="utf-8-sig", newline="") as f:
                reader = csv.DictReader(f)
                reader.fieldnames = [column.strip() for column in reader.fieldnames or []]
                self._check_header(reader.fieldnames)
                return [self._build_case(self._row_to_case(row, reader.line_num), reader.line_num) for row in reader]
        except OSError as e:
            raise CaseSourceError(self.path, f"Cannot read CSV: {e}") from e
        except csv.Error as e:
            raise CaseSourceError(self.path, f"Malformed CSV: {e}") from e

    def _check_header(self, columns: list[str]) -> None:
        if "id" not in columns:
            raise CaseSourceError(self.path, "Missing the required 'id' column.", row=1)
        for column in columns:
            if columns.count(column) > 1:
                raise CaseSourceError(self.path, "The column appears more than once.", row=1, column=column)
            prefix, _, path = column.partition(".")
            if prefix in DOTTED_PREFIXES and not path:
                raise CaseSourceError(self.path, f"'{prefix}.' must be followed by a field name.", row=1, column=column)

    def _row_to_case(self, row: dict[str, str | None], line: int) -> dict[str, Any]:
        if None in row:
            raise CaseSourceError(self.path, "Row has more cells than the header has columns.", row=line)
        case: dict[str, Any] = {"input": {}, "expected": {}, "extra": {}}
        for column, cell in row.items():
            if cell is None or cell.strip() == "":
                continue
            prefix, _, path = column.partition(".")
            if column in PLAIN_COLUMNS:
                case[column] = cell.strip()
            elif column in LIST_COLUMNS:
                case[column] = [item.strip() for item in cell.split(LIST_SEPARATOR) if item.strip()]
            else:
                try:
                    value = self._parse_cell(cell)
                    if prefix in DOTTED_PREFIXES:
                        self._set_path(case[prefix], path.split("."), value)
                    else:
                        case["extra"][column] = value
                except ValueError as e:
                    raise CaseSourceError(self.path, str(e), row=line, column=column) from e
        return case

    @staticmethod
    def _parse_cell(cell: str) -> Any:
        text = cell.strip()
        if not text.startswith(JSON_STARTS):
            return cell
        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            raise ValueError(f"Looks like JSON but does not parse: {e.msg}.") from e

    def _set_path(self, target: dict | list, segments: list[str], value: Any) -> None:
        """Set a value at a dotted path, creating dicts for names and lists for numeric segments."""
        head, rest = segments[0], segments[1:]
        if isinstance(target, list):
            if not head.isdigit():
                raise ValueError(f"'{head}' follows a list index, so it must be a number too.")
            index = int(head)
            target.extend([None] * (index + 1 - len(target)))
            existing = target[index]
        else:
            index = head
            existing = target.get(head)

        if not rest:
            if existing is not None:
                raise ValueError(f"'{head}' is set by more than one column.")
            target[index] = value
            return
        if existing is None:
            existing = [] if rest[0].isdigit() else {}
            target[index] = existing
        elif not isinstance(existing, (dict, list)):
            raise ValueError(f"'{head}' is set to a value and also used as a path.")
        self._set_path(existing, rest, value)
