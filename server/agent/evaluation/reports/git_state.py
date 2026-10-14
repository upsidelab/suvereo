import subprocess
from pathlib import Path

from pydantic import BaseModel


class GitState(BaseModel):
    """The commit a suite ran at and whether the working tree had uncommitted changes; None outside a git checkout."""

    sha: str | None = None
    dirty: bool | None = None

    @classmethod
    def of(cls, path: Path) -> "GitState":
        sha = cls._run_git(path, "rev-parse", "HEAD")
        if sha is None:
            return cls()
        return cls(sha=sha, dirty=bool(cls._run_git(path, "status", "--porcelain")))

    @staticmethod
    def _run_git(path: Path, *args: str) -> str | None:
        try:
            completed = subprocess.run(["git", "-C", str(path), *args], capture_output=True, text=True, timeout=10)
        except (OSError, subprocess.SubprocessError):
            return None
        return completed.stdout.strip() if completed.returncode == 0 else None
