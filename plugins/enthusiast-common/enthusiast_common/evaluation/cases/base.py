from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from ..errors import CaseSourceError
from ..suite import EvalCase


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
            case = EvalCase.model_validate(data)
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
        return "; ".join(f"{'.'.join(str(p) for p in e['loc']) or 'case'}: {e['msg']}" for e in error.errors())
