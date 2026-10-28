from pathlib import Path

from ..errors import CaseSourceError, DuplicateCaseError
from ..suite import CasesSpec, EvalCase
from .base import BaseCaseSource
from .directory_source import SOURCES_BY_SUFFIX, DirectoryCaseSource


class CaseCollector:
    """Gathers a suite's cases from files, directories and inline entries, rejecting duplicate ids."""

    def __init__(self, base_dir: Path):
        self.base_dir = base_dir

    def collect(self, spec: CasesSpec) -> list[EvalCase]:
        """Every case the spec points at, in the order written; raises CaseSourceError or DuplicateCaseError."""
        cases: list[EvalCase] = []
        origins: dict[str, str] = {}
        for entry in spec if isinstance(spec, list) else [spec]:
            if isinstance(entry, EvalCase):
                batches = [([self._resolve_inline(entry)], "the suite file")]
            else:
                batches = [(source.load(), str(source.path)) for source in self._sources_for(entry)]
            for loaded, origin in batches:
                for case in loaded:
                    if case.id in origins:
                        raise DuplicateCaseError(case.id, origins[case.id], origin)
                    origins[case.id] = origin
                    cases.append(case)
        return cases

    def _sources_for(self, entry: str) -> list[BaseCaseSource]:
        path = (self.base_dir / entry).resolve()
        if path.is_dir():
            return DirectoryCaseSource(path).file_sources()
        if not path.is_file():
            raise CaseSourceError(path, "No such case file or directory.")
        source_class = SOURCES_BY_SUFFIX.get(path.suffix.lower())
        if source_class is None:
            raise CaseSourceError(path, f"Unsupported case file type; use one of {', '.join(SOURCES_BY_SUFFIX)}.")
        return [source_class(path)]

    def _resolve_inline(self, case: EvalCase) -> EvalCase:
        files = []
        for file in case.files:
            resolved = (self.base_dir / file).resolve()
            if not resolved.is_file():
                raise CaseSourceError(self.base_dir, f"Inline case '{case.id}': file '{file}' does not exist.")
            files.append(resolved)
        return case.model_copy(update={"files": files})
