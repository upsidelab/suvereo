import asyncio
import inspect
import json
from abc import ABCMeta
from typing import Any, Callable, Dict, List, TypeVar, Union, get_args, get_origin

from pydantic import BaseModel, Json, model_validator
from pydantic._internal._model_construction import ModelMetaclass

T = TypeVar("T")


def _release_thread_local_db_connections() -> None:
    """Close any database connections the calling thread opened.

    Django keeps connections in thread-local storage and only tidies them up for threads it owns,
    which a worker thread borrowed from the event loop is not. Without this, each turn that runs
    sync ORM code off the loop opens a fresh connection and leaves it for garbage collection.

    Does nothing when the host is not a Django application.
    """
    try:
        from django.db import connections
    except ImportError:
        return
    connections.close_all()


async def run_off_event_loop(func: Callable[..., T], *args: Any) -> T:
    """Run blocking, database-touching code in a worker thread and hand back its result.

    Sync ORM calls cannot happen on a thread with a running event loop, so they are pushed onto a
    worker thread; the connections that opens are released before the thread is handed back.
    """
    return await asyncio.to_thread(_call_and_release_connections, func, *args)


def _call_and_release_connections(func: Callable[..., T], *args: Any) -> T:
    try:
        return func(*args)
    finally:
        _release_thread_local_db_connections()


def deep_merge(base: dict, patch: dict) -> dict:
    """Return ``base`` with ``patch`` merged in: nested dicts merge, any other value replaces. Neither is mutated."""
    merged = dict(base)
    for key, value in patch.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def prioritize_items(items: list[str], priorities: list[str]):
    items_set = set(items)
    priorities_set = set(priorities)

    result = [p for p in priorities if p in items_set]
    result += [item for item in items if item not in priorities_set]
    return result


def validate_required_vars(cls, name: str, required_vars: dict[str, type]):
    if inspect.isabstract(cls):
        return cls

    for var_name, expected_type in required_vars.items():
        if not hasattr(cls, var_name):
            raise TypeError(f"Class '{name}' must define class variable '{var_name}'")
        value = getattr(cls, var_name)
        if value is None:
            continue

        origin = get_origin(expected_type)

        if origin:
            if isinstance(value, origin):
                continue

        if isinstance(value, expected_type):
            continue

        if isinstance(value, type):
            if issubclass(value, expected_type):
                continue
        raise TypeError(
            f"Class variable '{var_name}' in '{name}' must be of type or subclass of '{expected_type.__name__}', "
            f"but got '{type(value).__name__ if not isinstance(value, type) else value.__name__}'"
        )
    return cls


class ExtraArgsClassBaseMeta(ABCMeta):
    REQUIRED_VARS: dict[str, Any] = {}
    OPTIONAL_VARS: dict[str, Any] = {}

    def __new__(mcs, name, bases, namespace, **kwargs):
        cls = super().__new__(mcs, name, bases, namespace, **kwargs)
        if namespace.get("__abstract__", False) or inspect.isabstract(cls):
            return cls
        cls._check_required_vars(name)
        cls._check_optional_vars(name)
        return cls

    def _check_required_vars(cls, name: str) -> None:
        validate_required_vars(cls, name, cls.REQUIRED_VARS)
        for var_name in cls.REQUIRED_VARS:
            if not getattr(cls, var_name):
                raise TypeError(f"Class '{name}' must define a non-empty class variable '{var_name}'")

    def _check_optional_vars(cls, name: str) -> None:
        defined_vars = {var_name: var_type for var_name, var_type in cls.OPTIONAL_VARS.items() if hasattr(cls, var_name)}
        validate_required_vars(cls, name, defined_vars)
        for var_name, expected_type in defined_vars.items():
            value = getattr(cls, var_name)
            if value is None or get_origin(expected_type) is not list:
                continue
            (item_type,) = get_args(expected_type)
            for item in value:
                if not isinstance(item, item_type):
                    raise TypeError(
                        f"Class variable '{var_name}' in '{name}' must hold '{item_type.__name__}' items, "
                        f"but got '{type(item).__name__}'"
                    )


class RequiredFieldsMeta(ModelMetaclass):
    MAX_DEPTH = 2

    def __new__(cls, name, bases, namespace):
        new_cls = super().__new__(cls, name, bases, namespace)

        def check_type_depth(annotation: Any, current_depth=1):
            if current_depth > cls.MAX_DEPTH:
                raise TypeError(f"Exceeded max depth of {cls.MAX_DEPTH} in field annotation")

            origin = get_origin(annotation)
            args = get_args(annotation)

            if origin is None:
                return

            if origin in {list, List, dict, Dict, Union, tuple}:
                for arg in args:
                    check_type_depth(arg, current_depth + 1)

        for field_name, field in getattr(new_cls, "model_fields", {}).items():
            check_type_depth(field.annotation)
        return new_cls


class RequiredFieldsModel(BaseModel, metaclass=RequiredFieldsMeta):
    @model_validator(mode="before")
    def convert_json_fields(cls, values: dict) -> dict:
        for name, field in cls.model_fields.items():
            if field.annotation is Json and name in values:
                v = values[name]
                if isinstance(v, dict):
                    values[name] = json.dumps(v)
        return values


class AgentAdditionalArguments(BaseModel):
    AGENT_ARGS: dict[str, str]
    PROMPT_INPUT: dict[str, str]
    TOOLS: list[dict[str, str]]
