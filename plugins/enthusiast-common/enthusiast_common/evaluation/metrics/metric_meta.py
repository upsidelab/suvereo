import inspect
from typing import get_args

from pydantic import BaseModel

from ...agents.base import ExtraArgsClassBaseMeta
from ..suite import SuiteKind

VALUE_TYPES = ("number", "bool", "label")


class MetricMeta(ExtraArgsClassBaseMeta):
    """Checks that a concrete metric declares its NAME, VALUE_TYPE and PARAMS, and only known KINDS, when the class
    is defined."""

    REQUIRED_VARS = {"NAME": str, "VALUE_TYPE": str, "PARAMS": BaseModel}

    def __new__(mcs, name, bases, namespace, **kwargs):
        cls = super().__new__(mcs, name, bases, namespace, **kwargs)
        if namespace.get("__abstract__", False) or inspect.isabstract(cls):
            return cls
        if cls.VALUE_TYPE not in VALUE_TYPES:
            raise TypeError(f"Metric '{name}' has VALUE_TYPE '{cls.VALUE_TYPE}'; use one of {', '.join(VALUE_TYPES)}.")
        kinds = get_args(SuiteKind)
        if not cls.KINDS or any(kind not in kinds for kind in cls.KINDS):
            raise TypeError(f"Metric '{name}' has KINDS {cls.KINDS!r}; use one or more of {', '.join(kinds)}.")
        return cls
