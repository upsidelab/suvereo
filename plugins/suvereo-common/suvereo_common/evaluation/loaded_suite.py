from pathlib import Path

from pydantic import BaseModel, ConfigDict

from .suite import EvalCase, EvalSuite


class LoadedSuite(BaseModel):
    """A suite read from disk, with its cases collected."""

    model_config = ConfigDict(frozen=True)

    path: Path
    suite: EvalSuite
    cases: list[EvalCase]

    @property
    def base_dir(self) -> Path:
        """Where suite-relative paths (cases, prompt files, data) resolve from."""
        return self.path.parent
