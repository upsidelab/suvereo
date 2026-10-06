import yaml

from ..errors import CaseSourceError
from ..suite import EvalCase
from .base import BaseCaseSource


class YamlCaseSource(BaseCaseSource):
    """A YAML file holding one case, or a list of cases."""

    def load(self) -> list[EvalCase]:
        try:
            data = yaml.safe_load(self.path.read_text(encoding="utf-8"))
        except (OSError, yaml.YAMLError) as e:
            raise CaseSourceError(self.path, f"Cannot read YAML: {e}") from e
        if data is None:
            return []
        if not isinstance(data, list):
            return [self._build_case(data)]
        cases = []
        for number, item in enumerate(data, start=1):
            try:
                cases.append(self._build_case(item))
            except CaseSourceError as e:
                raise CaseSourceError(self.path, f"case {number}: {e.message}") from e
        return cases
