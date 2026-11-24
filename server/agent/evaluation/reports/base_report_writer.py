from abc import ABC, abstractmethod
from pathlib import Path
from typing import ClassVar

from agent.evaluation.reports.suite_report import SuiteReport


class BaseReportWriter(ABC):
    NAME: ClassVar[str]

    @abstractmethod
    def write(self, report: SuiteReport, run_dir: Path) -> list[Path]:
        pass
