from abc import ABC, abstractmethod
from pathlib import Path
from typing import ClassVar

from .suite_report import SuiteReport


class BaseReportWriter(ABC):
    """Writes one of a suite run's outputs into its run directory; NAME is how suite.yaml's `reports:` selects it
    (a ReportName), or for summary.json, which is always written, just its name."""

    NAME: ClassVar[str]

    @abstractmethod
    def write(self, report: SuiteReport, run_dir: Path) -> list[Path]:
        """Write the output and return the files written."""
