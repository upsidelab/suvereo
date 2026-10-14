from abc import ABC, abstractmethod
from pathlib import Path
from typing import ClassVar

from enthusiast_common.evaluation.suite import ReportName

from .suite_report import SuiteReport


class BaseReportWriter(ABC):
    """Writes one of a suite run's outputs into its run directory; NAME is how suite.yaml's `reports:` selects it."""

    NAME: ClassVar[ReportName]

    @abstractmethod
    def write(self, report: SuiteReport, run_dir: Path) -> list[Path]:
        """Write the output and return the files written."""
