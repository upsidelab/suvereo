from suvereo_common.evaluation.suite import PassThreshold

from agent.evaluation.reports.csv_table import CsvTable
from agent.evaluation.reports.markdown_text import MarkdownText

WORDS = {"min": "≥", "max": "≤", "equals": "exactly", "in": "one of"}


def threshold_text(threshold: PassThreshold | None) -> str | None:
    if threshold is None:
        return None
    conditions = threshold.model_dump(by_alias=True, exclude_none=True)
    return ", ".join(f"{key} {CsvTable.cell(value)}" for key, value in conditions.items())


def threshold_words(threshold: PassThreshold) -> str:
    parts = []
    for key, value in threshold.model_dump(by_alias=True, exclude_none=True).items():
        if isinstance(value, bool):
            parts.append(str(value).lower())
        elif isinstance(value, list):
            options = ", ".join(str(v).lower() if isinstance(v, bool) else str(v) for v in value)
            parts.append(f"{WORDS[key]} {options}")
        else:
            parts.append(f"{WORDS.get(key, key)} {MarkdownText.cell(value)}")
    return " and ".join(parts)
