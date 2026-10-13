import asyncio
import builtins
import functools
import importlib
import inspect
import re
import string
import time
from abc import ABCMeta
from contextlib import contextmanager
from datetime import datetime
from threading import Lock
from types import SimpleNamespace
from typing import Any, ClassVar, Iterator, Mapping

from pydantic import TypeAdapter, ValidationError

from ..trace import MockCall, TraceRecorder
from .errors import MockConfigError, UnmockedCallError
from .mock_behaviour import MockBehaviour

BEHAVIOURS = TypeAdapter(MockBehaviour | list[MockBehaviour])
INSTANCE_ATTRIBUTES = frozenset({"data", "strict", "recorder", "calls"})
#: ``{name}``, ``{name[0]}``, ``{name.attr}`` or ``{name:spec}``; any other brace is literal text, JSON included.
PLACEHOLDER = re.compile(r"\{([A-Za-z_]\w*(?:\.[A-Za-z_]\w*|\[[^\[\]{}]*\])*)(?::([^{}]*))?\}")


class BaseMock:
    """Stands in for an interface: records every call, answers from declared behaviour, and generates the methods a subclass doesn't define."""

    INTERFACE: ClassVar[type]
    ERRORS: ClassVar[dict[str, type[Exception]]] = {}

    _declarative: ClassVar[dict[type, type["BaseMock"]]] = {}

    def __init_subclass__(cls, **kwargs: Any):
        super().__init_subclass__(**kwargs)
        interface = cls.__dict__.get("INTERFACE")
        if interface is None:
            return
        for name, original in cls.interface_methods().items():
            if name in vars(BaseMock) or name in INSTANCE_ATTRIBUTES:
                raise TypeError(f"{interface.__name__}.{name} clashes with a BaseMock attribute.")
            if not any(name in vars(klass) for klass in cls.__mro__[: cls.__mro__.index(BaseMock)]):
                setattr(cls, name, cls._recording_method(name, original))
        if isinstance(interface, ABCMeta):
            interface.register(cls)

    def __init__(
        self,
        behaviour: Mapping[str, Any] | None = None,
        data: dict[str, Any] | None = None,
        strict: bool = False,
        recorder: TraceRecorder | None = None,
    ):
        """Create a mock; raises MockConfigError for an unknown method or error, or an invalid behaviour.

        Args:
            behaviour: Per method name, a behaviour or a list of them; the first whose when matches applies.
            data: Read by a subclass's stateful logic, e.g. a catalog.
            strict: Raise UnmockedCallError for calls no behaviour answers, instead of returning None.
            recorder: Also records every call into a run's trace.
        """
        self.data = data or {}
        self.strict = strict
        self.recorder = recorder
        self.calls: list[MockCall] = []
        self._behaviour = self._parse_behaviours(behaviour or {})
        self._lock = Lock()
        self._call_counts: dict[str, int] = {}
        self._sequence_positions: dict[int, int] = {}

    @classmethod
    def declarative(cls, interface: type) -> type["BaseMock"]:
        """A mock class for any interface, driven by declared behaviour alone; one cached class per interface."""
        if interface not in BaseMock._declarative:
            BaseMock._declarative[interface] = type(
                f"Declarative{interface.__name__}Mock", (BaseMock,), {"INTERFACE": interface}
            )
        return BaseMock._declarative[interface]

    @classmethod
    def interface_methods(cls) -> dict[str, Any]:
        """The interface's public instance methods, inherited ones included, by name."""
        return {
            name: member
            for name, member in inspect.getmembers(cls.INTERFACE, inspect.isfunction)
            if not name.startswith("_") and not isinstance(inspect.getattr_static(cls.INTERFACE, name), staticmethod)
        }

    def calls_to(self, method: str) -> list[MockCall]:
        """The calls this mock received to one method, in order."""
        return [c for c in self.calls if c.method == method]

    def reset(self) -> None:
        """Forget recorded calls, call numbers and sequence positions; behaviour and data are kept."""
        with self._lock:
            self.calls.clear()
            self._call_counts.clear()
            self._sequence_positions.clear()

    def _handle_call(self, method: str, args: tuple, kwargs: dict[str, Any]) -> Any:
        with self._record_call(method, args, kwargs) as outcome:
            outcome.arguments = self._bind_arguments(method, args, kwargs)
            behaviour, context = self._find_behaviour(method, outcome.arguments, args, kwargs)
            if behaviour is not None and behaviour.latency_ms:
                time.sleep(behaviour.latency_ms / 1000)
            outcome.result = self._answer_call(method, behaviour, context, args, kwargs)
        return outcome.result

    async def _handle_call_async(self, method: str, args: tuple, kwargs: dict[str, Any]) -> Any:
        with self._record_call(method, args, kwargs) as outcome:
            outcome.arguments = self._bind_arguments(method, args, kwargs)
            behaviour, context = self._find_behaviour(method, outcome.arguments, args, kwargs)
            if behaviour is not None and behaviour.latency_ms:
                await asyncio.sleep(behaviour.latency_ms / 1000)
            outcome.result = self._answer_call(method, behaviour, context, args, kwargs)
        return outcome.result

    @contextmanager
    def _record_call(self, method: str, args: tuple, kwargs: dict[str, Any]) -> Iterator[SimpleNamespace]:
        started_at, started = datetime.now(), time.perf_counter()
        outcome = SimpleNamespace(result=None, arguments={})
        error = None
        try:
            yield outcome
        except Exception as e:
            error = f"{type(e).__name__}: {e}"
            raise
        finally:
            call = MockCall(
                method=method,
                args=list(args),
                kwargs=kwargs,
                arguments=outcome.arguments,
                result=outcome.result,
                error=error,
                started_at=started_at,
                duration_ms=(time.perf_counter() - started) * 1000,
            )
            with self._lock:
                self.calls.append(call)
            if self.recorder is not None:
                self.recorder.record_mock_call(call)

    def _find_behaviour(
        self, method: str, arguments: dict[str, Any], args: tuple, kwargs: dict[str, Any]
    ) -> tuple[MockBehaviour | None, dict[str, Any]]:
        with self._lock:
            number = self._call_counts[method] = self._call_counts.get(method, 0) + 1
        behaviour = next((b for b in self._behaviour.get(method, []) if b.matches(arguments)), None)
        return behaviour, {**arguments, "n": number, "args": args, "kwargs": kwargs}

    def _answer_call(
        self, method: str, behaviour: MockBehaviour | None, context: dict[str, Any], args: tuple, kwargs: dict[str, Any]
    ) -> Any:
        if behaviour is None:
            return self._answer_unmatched_call(method, *args, **kwargs)
        return self._apply_behaviour(behaviour, context)

    def _answer_unmatched_call(self, method: str, *args: Any, **kwargs: Any) -> Any:
        """Answer a call no behaviour matched: None, or UnmockedCallError when strict. Override for stateful logic."""
        if self.strict:
            raise UnmockedCallError(f"{self.INTERFACE.__name__}.{method} has no declared behaviour for this call.")
        return None

    def _apply_behaviour(self, behaviour: MockBehaviour, context: dict[str, Any]) -> Any:
        if behaviour.raises is not None:
            raise self._resolve_error_class(behaviour.raises.error)(
                self._fill_placeholders(behaviour.raises.message, context)
            )
        if behaviour.sequence is not None:
            with self._lock:
                position = self._sequence_positions.get(id(behaviour), 0)
                self._sequence_positions[id(behaviour)] = position + 1
            return self._fill_placeholders(behaviour.sequence[min(position, len(behaviour.sequence) - 1)], context)
        return self._fill_placeholders(behaviour.returns, context)

    def _bind_arguments(self, method: str, args: tuple, kwargs: dict[str, Any]) -> dict[str, Any]:
        signature = inspect.signature(getattr(self.INTERFACE, method))
        bound = signature.bind(None, *args, **kwargs)
        bound.apply_defaults()
        arguments: dict[str, Any] = {}
        for name, value in list(bound.arguments.items())[1:]:
            if signature.parameters[name].kind is inspect.Parameter.VAR_KEYWORD:
                arguments.update(value)
            else:
                arguments[name] = value
        return arguments

    def _parse_behaviours(self, behaviour: Mapping[str, Any]) -> dict[str, list[MockBehaviour]]:
        known = self.interface_methods()
        parsed: dict[str, list[MockBehaviour]] = {}
        for method, declared in behaviour.items():
            if method not in known:
                raise MockConfigError(
                    f"{self.INTERFACE.__name__} has no method '{method}'; it has: {', '.join(sorted(known))}."
                )
            try:
                value = BEHAVIOURS.validate_python(declared)
            except ValidationError as e:
                raise MockConfigError(f"Invalid behaviour for '{method}': {e}") from e
            parsed[method] = value if isinstance(value, list) else [value]
            for b in parsed[method]:
                if b.raises is not None:
                    self._resolve_error_class(b.raises.error)
                self._check_when_arguments(method, known[method], b)
        return parsed

    def _check_when_arguments(self, method: str, function: Any, behaviour: MockBehaviour) -> None:
        if not behaviour.when:
            return
        parameters = list(inspect.signature(function).parameters.values())[1:]
        if any(p.kind is inspect.Parameter.VAR_KEYWORD for p in parameters):
            return
        names = {p.name for p in parameters}
        if unknown := sorted(set(behaviour.when) - names):
            raise MockConfigError(
                f"'when' for '{method}' names {', '.join(unknown)}, which it does not take; "
                f"it takes: {', '.join(sorted(names)) or 'nothing'}."
            )

    def _resolve_error_class(self, name: str) -> type[Exception]:
        candidate = self.ERRORS.get(name) or getattr(builtins, name, None)
        if candidate is None and "." in name:
            module, _, attribute = name.rpartition(".")
            try:
                candidate = getattr(importlib.import_module(module), attribute, None)
            except ImportError as e:
                raise MockConfigError(f"Cannot import error '{name}'.") from e
        if not (isinstance(candidate, type) and issubclass(candidate, Exception)):
            raise MockConfigError(
                f"Unknown error '{name}'; use a builtin, a dotted path or one of {sorted(self.ERRORS)}."
            )
        return candidate

    @classmethod
    def _fill_placeholders(cls, value: Any, context: dict[str, Any]) -> Any:
        if isinstance(value, str):
            return PLACEHOLDER.sub(lambda match: cls._fill_placeholder(match, value, context), value)
        if isinstance(value, list):
            return [cls._fill_placeholders(v, context) for v in value]
        if isinstance(value, dict):
            return {k: cls._fill_placeholders(v, context) for k, v in value.items()}
        return value

    @staticmethod
    def _fill_placeholder(match: re.Match, template: str, context: dict[str, Any]) -> str:
        field, spec = match.group(1), match.group(2) or ""
        try:
            return format(string.Formatter().get_field(field, (), context)[0], spec)
        except (KeyError, IndexError, AttributeError, ValueError, TypeError) as e:
            raise MockConfigError(f"Template '{template}' cannot fill {{{field}}} for this call: {e!r}") from e

    @staticmethod
    def _recording_method(name: str, original: Any) -> Any:
        if inspect.iscoroutinefunction(original):

            async def method(self, *args, **kwargs):
                return await self._handle_call_async(name, args, kwargs)
        else:

            def method(self, *args, **kwargs):
                return self._handle_call(name, args, kwargs)

        functools.update_wrapper(method, original)
        method.__isabstractmethod__ = False
        return method
