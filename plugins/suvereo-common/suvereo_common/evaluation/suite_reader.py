from pathlib import Path

import yaml
from pydantic import ValidationError

from .cases import CaseCollector
from .errors import EvalSuiteError
from .loaded_suite import LoadedSuite
from .suite import EvalSuite


class SuiteReader:
    """Reads suite.yaml and its cases, checking what needs no host; the host checks the rest."""

    def read(self, path: Path) -> LoadedSuite:
        """Read a suite file and collect its cases; raises EvalSuiteError (or CaseSourceError, DuplicateCaseError)."""
        path = path.resolve()
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
        except (OSError, yaml.YAMLError) as e:
            raise EvalSuiteError(f"{path}: cannot read the suite: {e}") from e
        if not isinstance(data, dict):
            raise EvalSuiteError(f"{path}: a suite must be a mapping.")
        try:
            suite = EvalSuite.model_validate(data)
        except ValidationError as e:
            raise EvalSuiteError(f"{path}: invalid suite:\n{e}") from e
        if not suite.name:
            suite = suite.model_copy(update={"name": path.parent.name})
        return LoadedSuite(path=path, suite=suite, cases=CaseCollector(path.parent).collect(suite.cases))
