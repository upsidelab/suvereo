import inspect

from pydantic import BaseModel

from ...agents.base import ExtraArgsClassBaseMeta

VALUE_TYPES = ("number", "bool", "label")


class MetricMeta(ExtraArgsClassBaseMeta):
    """Checks that a concrete metric declares its NAME, VALUE_TYPE and PARAMS when the class is defined."""

    REQUIRED_VARS = {"NAME": str, "VALUE_TYPE": str, "PARAMS": BaseModel}

    def __new__(mcs, name, bases, namespace, **kwargs):
        cls = super().__new__(mcs, name, bases, namespace, **kwargs)
        if (
            not namespace.get("__abstract__", False)
            and not inspect.isabstract(cls)
            and cls.VALUE_TYPE not in VALUE_TYPES
        ):
            raise TypeError(f"Metric '{name}' has VALUE_TYPE '{cls.VALUE_TYPE}'; use one of {', '.join(VALUE_TYPES)}.")
        return cls
