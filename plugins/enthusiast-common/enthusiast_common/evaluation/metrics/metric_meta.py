from pydantic import BaseModel

from ...utils import ExtraArgsClassBaseMeta
from ..suite import SuiteKind

VALUE_TYPES = ("number", "bool", "label")


class MetricMeta(ExtraArgsClassBaseMeta):
    """Checks that a concrete metric declares its NAME, VALUE_TYPE and PARAMS, and only known KINDS, when the class
    is defined."""

    REQUIRED_VARS = {"NAME": str, "VALUE_TYPE": str}
    OPTIONAL_VARS = {"PARAMS": BaseModel}

    def _check_required_vars(cls, name: str) -> None:
        super()._check_required_vars(name)
        if cls.VALUE_TYPE not in VALUE_TYPES:
            raise TypeError(f"Metric '{name}' has VALUE_TYPE '{cls.VALUE_TYPE}'; use one of {', '.join(VALUE_TYPES)}.")

    def _check_optional_vars(cls, name: str) -> None:
        super()._check_optional_vars(name)
        if not cls.KINDS or any(not isinstance(kind, SuiteKind) for kind in cls.KINDS):
            raise TypeError(f"Metric '{name}' has KINDS {cls.KINDS!r}; use one or more of {', '.join(SuiteKind)}.")
