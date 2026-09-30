import sys
from types import ModuleType
from typing import Dict, List

import pytest
from pydantic import BaseModel, Field
from utils.functions import (
    DurationUnit,
    extract_type_info,
    get_model_descriptor_from_class_field,
    import_from_string,
    parse_duration,
)


class SimpleModel(BaseModel):
    name: str = Field(description="A name", title="Name")
    age: int


class ListModel(BaseModel):
    tags: List[str] = Field(description="List of tags")


class DictModel(BaseModel):
    mapping: Dict[str, int] = Field(title="Mapping field")


class DummySimple:
    ARGS_FIELD = SimpleModel


class DummyList:
    ARGS_FIELD = ListModel


class DummyDict:
    ARGS_FIELD = DictModel


dummy_module = ModuleType("dummy_module")
dummy_module.DummySimple = DummySimple
dummy_module.DummyList = DummyList
dummy_module.DummyDict = DummyDict
sys.modules["dummy_module"] = dummy_module


def test_import_from_string_valid():
    cls = import_from_string("dummy_module.DummySimple")
    assert cls == DummySimple


def test_import_from_string_invalid_module():
    with pytest.raises(ModuleNotFoundError):
        import_from_string("nonexistent.module.Class")


def test_import_from_string_invalid_format():
    with pytest.raises(ValueError):
        import_from_string("invalidformatstring")


def test_import_from_string_invalid_class():
    with pytest.raises(AttributeError):
        import_from_string("dummy_module.MissingClass")


def test_extract_type_info_simple():
    info = extract_type_info(str)

    assert info == {"container": None, "inner_type": "str"}


def test_extract_type_info_list():
    info = extract_type_info(List[str])

    assert info["container"] == "list"
    assert info["inner_type"] == {"container": None, "inner_type": "str"}


def test_extract_type_info_dict():
    info = extract_type_info(Dict[str, int])

    assert info == {"container": "dict", "key_type": "str", "value_type": "int"}


def test_extract_type_info_no_args_dict():
    from typing import Dict as TypingDict

    info = extract_type_info(TypingDict)

    assert info == {"container": "dict", "key_type": "Any", "value_type": "Any"}


def test_get_model_descriptor_from_class_field_simple():
    desc = get_model_descriptor_from_class_field(DummySimple, "ARGS_FIELD")

    assert "name" in desc
    assert desc["name"]["type"] == {"container": None, "inner_type": "str"}
    assert desc["name"]["description"] == "A name"
    assert desc["name"]["title"] == "Name"
    assert "age" in desc
    assert desc["age"]["type"] == {"container": None, "inner_type": "int"}


def test_get_model_descriptor_from_class_field_list():
    desc = get_model_descriptor_from_class_field(DummyList, "ARGS_FIELD")

    assert "tags" in desc
    assert desc["tags"]["type"]["container"] == "list"
    assert desc["tags"]["type"]["inner_type"] == {"container": None, "inner_type": "str"}


def test_get_model_descriptor_from_class_field_dict():
    desc = get_model_descriptor_from_class_field(DummyDict, "ARGS_FIELD")

    assert "mapping" in desc
    assert desc["mapping"]["type"] == {"container": "dict", "key_type": "str", "value_type": "int"}
    assert desc["mapping"]["title"] == "Mapping field"


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("500ms", 500),
        ("30s", 30_000),
        ("15m", 15 * 60_000),
        ("12h", 12 * 3_600_000),
        ("7d", 7 * 86_400_000),
        (" 7d ", 7 * 86_400_000),
    ],
)
def test_parses_supported_units_into_milliseconds_by_default(value, expected):
    assert parse_duration(value) == expected


@pytest.mark.parametrize(
    ("value", "unit", "expected"),
    [
        ("10s", DurationUnit.SECONDS, 10),
        ("2h", DurationUnit.MINUTES, 120),
        ("7d", DurationUnit.DAYS, 7),
    ],
)
def test_converts_into_the_requested_unit(value, unit, expected):
    assert parse_duration(value, unit=unit) == expected


def test_rejects_a_duration_that_is_not_a_whole_number_of_the_unit():
    with pytest.raises(ValueError):
        parse_duration("90s", unit=DurationUnit.MINUTES)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("250msec", 250),
        ("5sec", 5_000),
        ("15min", 15 * 60_000),
        ("15minutes", 15 * 60_000),
        ("1minute", 60_000),
        ("2hrs", 2 * 3_600_000),
        ("1day", 86_400_000),
    ],
)
def test_accepts_unit_aliases(value, expected):
    assert parse_duration(value) == expected


def test_error_lists_every_accepted_suffix():
    with pytest.raises(ValueError, match="ms, msec, .*, days$"):
        parse_duration("2w")


@pytest.mark.parametrize("value", ["", "15", "m", "15 m", "1.5h", "2w", "-5m"])
def test_rejects_malformed_values(value):
    with pytest.raises(ValueError):
        parse_duration(value)
