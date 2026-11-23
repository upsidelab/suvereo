from dataclasses import dataclass
from pathlib import Path

CONVENTIONS = "server/AGENTS.md#code-conventions"

# Where an agent reads the convention behind a rule, by rule code prefix.
CONVENTION_SOURCES = {
    "ANN": CONVENTIONS,
    "D1": "plugins/suvereo-common/AGENTS.md",
    "TID252": CONVENTIONS,
    "ERA001": CONVENTIONS,
    "CV001": CONVENTIONS,
    "CV002": CONVENTIONS,
    "CV003": "server/AGENTS.md#code-structure",
    "CV004": "server/AGENTS.md#code-structure",
}


@dataclass(frozen=True)
class Violation:
    path: Path
    line: int
    code: str
    message: str

    @property
    def key(self) -> str:
        return f"{self.path.as_posix()}::{self.code}"

    def __str__(self) -> str:
        source = next((doc for prefix, doc in CONVENTION_SOURCES.items() if self.code.startswith(prefix)), None)
        hint = f" (see {source})" if source else ""
        return f"{self.path.as_posix()}:{self.line}: {self.code} {self.message}{hint}"
