import logging
import os
import secrets
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

RESULTS_DIR = "results"
LATEST = "latest"


class RunDirectory:
    """Where one suite run's outputs go: <suite_dir>/results/<YYYYmmdd-HHMMSS>-<id>/, with results/latest linking to
    the newest run."""

    @staticmethod
    def create(suite_dir: Path, now: datetime | None = None) -> Path:
        """Create the run's directory and point results/latest at it; a failed link is logged, not raised."""
        results = suite_dir / RESULTS_DIR
        run_dir = results / f"{(now or datetime.now()):%Y%m%d-%H%M%S}-{secrets.token_hex(3)}"
        run_dir.mkdir(parents=True)
        latest = results / LATEST
        temporary = results / f".{LATEST}-{run_dir.name}"
        try:
            temporary.symlink_to(run_dir.name, target_is_directory=True)
            os.replace(temporary, latest)
        except OSError:
            temporary.unlink(missing_ok=True)
            logger.warning("Could not point %s at %s", latest, run_dir.name, exc_info=True)
        return run_dir
