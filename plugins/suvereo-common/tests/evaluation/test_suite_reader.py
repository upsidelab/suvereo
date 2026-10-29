import pytest
from suvereo_common.evaluation.errors import EvalSuiteError
from suvereo_common.evaluation.suite import EvalSuite
from suvereo_common.evaluation.suite_reader import SuiteReader


class TestSuiteReader:
    def test_reads_the_suite_and_its_cases(self, tmp_path):
        suite_dir = tmp_path / "order_intake"
        suite_dir.mkdir()
        (suite_dir / "cases.csv").write_text("id\na\nb\n")
        (suite_dir / "suite.yaml").write_text(
            "agent: {id: 12}\nmetrics: [{type: mock_calls, pass_threshold: {min: 0.95}}]\ncases: cases.csv\n"
        )

        loaded = SuiteReader().read(suite_dir / "suite.yaml")

        assert loaded.suite.name == "order_intake"
        assert [c.id for c in loaded.cases] == ["a", "b"]
        assert loaded.base_dir == suite_dir.resolve()

    @pytest.mark.parametrize(
        "text, message",
        [("- a list\n", "mapping"), ("agent: {id: 1}\ncases: c.csv\n", "metrics"), ("agent: [\n", "cannot read")],
    )
    def test_invalid_suites_name_the_file(self, tmp_path, text, message):
        path = tmp_path / "suite.yaml"
        path.write_text(text)

        with pytest.raises(EvalSuiteError, match=message):
            SuiteReader().read(path)


class TestEvalSuiteJsonSchema:
    def test_uses_the_yaml_spelling_of_aliased_keys(self):
        schema = EvalSuite.json_schema()

        assert "class" in schema["$defs"]["IntegrationConfig"]["properties"]
        assert "in" in schema["$defs"]["PassThreshold"]["properties"]
        assert "class" in schema["$defs"]["SimulatedUserConfig"]["properties"]
        assert schema["$defs"]["SuiteKind"]["enum"] == ["execution", "conversation"]
        assert set(schema["required"]) == {"agent", "metrics", "cases"}
