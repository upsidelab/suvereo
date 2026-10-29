import json

import pytest
from suvereo_common.evaluation.mocks import FixtureRecords, MockConfigError


class TestFixtureRecords:
    def test_inline_records_are_used_as_they_are(self, tmp_path):
        assert FixtureRecords.load([{"sku": "a"}], tmp_path) == [{"sku": "a"}]
        assert FixtureRecords.load(None, tmp_path) == []

    @pytest.mark.parametrize(
        "name, text",
        [
            ("rows.yaml", "- {sku: a}\n"),
            ("rows.json", json.dumps([{"sku": "a"}])),
            ("rows.csv", "sku\na\n"),
        ],
    )
    def test_files_are_read_relative_to_the_base_directory(self, tmp_path, name, text):
        (tmp_path / name).write_text(text)

        assert FixtureRecords.load(name, tmp_path) == [{"sku": "a"}]

    @pytest.mark.parametrize(
        "name, text, message",
        [
            ("rows.txt", "a", "Cannot read fixture file"),
            ("rows.yaml", "sku: a\n", "list of mappings"),
            ("missing.yaml", None, "missing"),
        ],
    )
    def test_unusable_records_are_reported(self, tmp_path, name, text, message):
        if text is not None:
            (tmp_path / name).write_text(text)

        with pytest.raises(MockConfigError, match=message):
            FixtureRecords.load(name, tmp_path)
