import yaml
from suvereo_common.evaluation.cases.base import BaseCaseSource
from suvereo_common.evaluation.errors import CaseSourceError
from suvereo_common.evaluation.suite import EvalCase


class YamlCaseSource(BaseCaseSource):
    """A YAML file holding one case, or a list of cases."""

    def load(self) -> list[EvalCase]:
        """Load the cases from the YAML file."""
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
