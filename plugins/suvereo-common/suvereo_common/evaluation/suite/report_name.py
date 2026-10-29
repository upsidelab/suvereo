from typing import Literal

ReportName = Literal["report", "results", "comparison", "cases", "metrics", "traces", "transcripts"]
DEFAULT_REPORTS: list[ReportName] = ["report", "results"]
