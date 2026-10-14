from enthusiast_common.evaluation.suite import Gate

from .csv_table import CsvTable


def gate_text(gate: Gate | None) -> str | None:
    """A gate as text in the reports' conventions, e.g. "min 0.95, max 1", "equals true" or "in a;b"."""
    if gate is None:
        return None
    conditions = gate.model_dump(by_alias=True, exclude_none=True)
    return ", ".join(f"{key} {CsvTable.cell(value)}" for key, value in conditions.items())
