from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from pydantic import TypeAdapter, ValidationError

from ..errors import CaseSourceError
from ..suite import AnyEvalCase, EvalCase, SuiteKind

CASE = TypeAdapter(AnyEvalCase)


class BaseCaseSource(ABC):
    """Reads test cases from one file, resolving their files relative to it."""

    def __init__(self, path: Path):
        self.path = path

    @abstractmethod
    def load(self) -> list[EvalCase]:
        """Every case in the source, files resolved to absolute paths; raises CaseSourceError for an invalid one."""

    def _build_case(self, data: Any, row: int | None = None) -> EvalCase:
        if not isinstance(data, dict):
            raise CaseSourceError(self.path, f"A case must be a mapping, got {type(data).__name__}.", row=row)
        try:
            case = CASE.validate_python(data)
        except ValidationError as e:
            raise CaseSourceError(self.path, self._describe(e), row=row) from e
        return case.model_copy(update={"files": [self._resolve_file(f, row) for f in case.files]})

    def _resolve_file(self, file: Path, row: int | None) -> Path:
        base = self.path if self.path.is_dir() else self.path.parent
        resolved = (base / file).resolve()
        if not resolved.is_file():
            raise CaseSourceError(self.path, f"File '{file}' does not exist (looked in {base}).", row=row)
        return resolved

    @staticmethod
    def _describe(error: ValidationError) -> str:
        """Each problem as 'field: message', naming the kind of case it was read as."""
        problems = []
        for e in error.errors():
            location, kind = list(e["loc"]), None
            if location and location[0] in set(SuiteKind):
                kind = location.pop(0)
            where = ".".join(str(p) for p in location) or "case"
            problems.append(f"{where}: {e['msg']}" + (f" ({kind} case)" if kind else ""))
        return "; ".join(problems)
