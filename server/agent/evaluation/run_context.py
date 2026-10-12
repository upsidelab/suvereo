from contextlib import contextmanager
from contextvars import ContextVar
from pathlib import Path
from typing import ClassVar, Iterator, Optional

from enthusiast_common.evaluation.trace import TraceRecorder
from enthusiast_common.integrations import BaseIntegration, BaseIntegrationPluginResolver


class EvalRunContext:
    """One evaluation run's state, read via current() by classes the agent builder instantiates without arguments."""

    _current: ClassVar[ContextVar[Optional["EvalRunContext"]]] = ContextVar("eval_run_context", default=None)

    def __init__(
        self,
        recorder: TraceRecorder,
        integrations: list[BaseIntegration] | None = None,
        real_resolver: type[BaseIntegrationPluginResolver] | None = None,
        base_dir: Path | None = None,
    ):
        self.recorder = recorder
        self.integrations = integrations or []
        #: The resolver to fall back to for interfaces no mock covers; None refuses real integrations.
        self.real_resolver = real_resolver
        self.base_dir = base_dir or Path.cwd()

    @classmethod
    def current(cls) -> Optional["EvalRunContext"]:
        """The run in progress on this thread or task, or None outside an evaluation."""
        return cls._current.get()

    @contextmanager
    def activate(self) -> Iterator["EvalRunContext"]:
        """Make this the current run for the duration of the block."""
        token = self._current.set(self)
        try:
            yield self
        finally:
            self._current.reset(token)
