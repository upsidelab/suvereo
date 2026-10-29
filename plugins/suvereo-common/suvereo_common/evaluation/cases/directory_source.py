from ..suite import EvalCase
from .base import BaseCaseSource
from .csv_source import CsvCaseSource
from .yaml_source import YamlCaseSource

SOURCES_BY_SUFFIX = {".yaml": YamlCaseSource, ".yml": YamlCaseSource, ".csv": CsvCaseSource}
SUITE_FILE_NAMES = ("suite.yaml", "suite.yml")


class DirectoryCaseSource(BaseCaseSource):
    """The YAML and CSV case files directly in a directory, skipping suite.yaml, subdirectories and input files."""

    def load(self) -> list[EvalCase]:
        return [case for source in self.file_sources() for case in source.load()]

    def file_sources(self) -> list[BaseCaseSource]:
        """One source per case file, in name order, so callers can tell which file a case came from."""
        files = sorted(
            p
            for p in self.path.iterdir()
            if p.is_file() and p.suffix.lower() in SOURCES_BY_SUFFIX and p.name.lower() not in SUITE_FILE_NAMES
        )
        return [SOURCES_BY_SUFFIX[file.suffix.lower()](file) for file in files]
