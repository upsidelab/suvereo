import pytest
from suvereo_common.evaluation.cases import YamlCaseSource
from suvereo_common.evaluation.errors import CaseSourceError


class TestYamlCaseSource:
    def test_reads_one_case_with_files_relative_to_it(self, tmp_path):
        (tmp_path / "big-order.pdf").write_bytes(b"%PDF")
        path = tmp_path / "big-order.yaml"
        path.write_text(
            "id: big-order\n"
            "tags: [multi-page]\n"
            "files: [big-order.pdf]\n"
            "expected: {mock_calls: {create_order_with_items: [{items: [[SKU-1, 2]]}]}}\n"
            "integrations:\n"
            "  - class: mocks.ECommerceMockIntegration\n"
            "    config: {behaviour: {create_order_with_items: {raises: {error: X}}}}\n"
            "metrics:\n"
            "  - {type: trace_event, name: stopped_cleanly, params: {event: stop_execution}}\n"
        )

        case = YamlCaseSource(path).load()[0]

        assert case.files == [(tmp_path / "big-order.pdf").resolve()]
        assert case.integrations[0].class_path == "mocks.ECommerceMockIntegration"
        assert case.metrics[0].name == "stopped_cleanly"

    def test_reads_a_list_of_cases(self, tmp_path):
        path = tmp_path / "cases.yaml"
        path.write_text("- id: a\n- id: b\n")

        assert [c.id for c in YamlCaseSource(path).load()] == ["a", "b"]

    def test_an_invalid_case_in_a_list_is_named_by_position(self, tmp_path):
        path = tmp_path / "cases.yaml"
        path.write_text("- id: a\n- id: b\n  tag: typo\n")

        with pytest.raises(CaseSourceError, match="case 2: tag"):
            YamlCaseSource(path).load()

    def test_an_empty_file_has_no_cases(self, tmp_path):
        path = tmp_path / "empty.yaml"
        path.write_text("")

        assert YamlCaseSource(path).load() == []

    @pytest.mark.parametrize(
        "text, message",
        [("id: a\nunknown_key: 1\n", "unknown_key"), ("- just a string\n", "mapping"), ("id: [unclosed\n", "YAML")],
    )
    def test_errors_name_the_file(self, tmp_path, text, message):
        path = tmp_path / "bad.yaml"
        path.write_text(text)

        with pytest.raises(CaseSourceError, match=message) as e:
            YamlCaseSource(path).load()

        assert e.value.path == path
