import importlib
import re
from enum import StrEnum
from typing import Any, get_args, get_origin

from pydantic_core import PydanticUndefined


class DurationUnit(StrEnum):
    """Units understood by `parse_duration`, both as a value suffix and as the unit to convert into."""

    MILLISECONDS = "ms"
    SECONDS = "s"
    MINUTES = "m"
    HOURS = "h"
    DAYS = "d"

    @property
    def milliseconds(self) -> int:
        """Length of one unit in milliseconds."""
        return _DURATION_UNIT_MILLISECONDS[self]


_DURATION_UNIT_MILLISECONDS = {
    DurationUnit.MILLISECONDS: 1,
    DurationUnit.SECONDS: 1000,
    DurationUnit.MINUTES: 60 * 1000,
    DurationUnit.HOURS: 60 * 60 * 1000,
    DurationUnit.DAYS: 24 * 60 * 60 * 1000,
}
_DURATION_UNIT_ALIASES = {
    DurationUnit.MILLISECONDS: ["ms", "msec", "millisecond", "milliseconds"],
    DurationUnit.SECONDS: ["s", "sec", "secs", "second", "seconds"],
    DurationUnit.MINUTES: ["m", "min", "mins", "minute", "minutes"],
    DurationUnit.HOURS: ["h", "hr", "hrs", "hour", "hours"],
    DurationUnit.DAYS: ["d", "day", "days"],
}
_DURATION_SUFFIXES = {alias: unit for unit, aliases in _DURATION_UNIT_ALIASES.items() for alias in aliases}
_DURATION_PATTERN = re.compile(r"^(\d+)([a-z]+)$")


def import_from_string(path: str):
    module_path, class_name = path.rsplit(".", 1)
    module = importlib.import_module(module_path)
    return getattr(module, class_name)


def extract_type_info(annotation) -> dict:
    origin = get_origin(annotation)
    args = get_args(annotation)
    if origin is list:
        return {"container": "list", "inner_type": extract_type_info(args[0])}

    if origin is dict:
        key_type = args[0].__name__ if args else "Any"
        value_type = args[1].__name__ if args else "Any"
        return {
            "container": "dict",
            "key_type": key_type,
            "value_type": value_type,
        }

    return {"container": None, "inner_type": annotation.__name__}


def get_model_descriptor_from_class_field(class_obj: Any, field_name: str) -> dict:
    model = getattr(class_obj, field_name)
    if model is None:
        return {}
    args = {}
    for field_name, field in model.model_fields.items():
        args[field_name] = {
            "type": extract_type_info(field.annotation),
            "description": field.description,
            "title": field.title or field_name,
            "required": field.is_required(),
        }

    return args


def get_model_descriptor_default_value_from_class(class_obj: Any, field_name: str) -> dict:
    model = getattr(class_obj, field_name)
    if model is None:
        return {}
    args = {}
    for field_name, field in model.model_fields.items():
        if field.default is None or field.default is PydanticUndefined:
            continue
        args[field_name] = field.default
    return args


def parse_duration(value: str, unit: DurationUnit = DurationUnit.MILLISECONDS) -> int:
    """Parse a compact duration such as `500ms`, `30s`, `15min`, `12hours` or `7d` into a whole number of `unit`s.

    The suffix may be any alias in `_DURATION_UNIT_ALIASES`. Raises `ValueError` for a malformed value or a
    duration that isn't a whole number of `unit`s (e.g. `90s` in minutes).
    """
    match = _DURATION_PATTERN.match(value.strip())
    value_unit = _DURATION_SUFFIXES.get(match.group(2)) if match else None
    if value_unit is None:
        raise ValueError(
            f"Invalid duration {value!r}, expected a number followed by one of: {', '.join(_DURATION_SUFFIXES)}"
        )
    amount_in_unit, remainder = divmod(int(match.group(1)) * value_unit.milliseconds, unit.milliseconds)
    if remainder:
        raise ValueError(f"Duration {value!r} is not a whole number of {unit.name.lower()}")
    return amount_in_unit
