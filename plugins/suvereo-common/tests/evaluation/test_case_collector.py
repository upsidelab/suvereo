import pytest
from suvereo_common.evaluation.cases import CaseCollector
from suvereo_common.evaluation.errors import CaseSourceError, DuplicateCaseError
from suvereo_common.evaluation.suite import EvalCase


@pytest.fixture
def suite_dir(tmp_path):
    (tmp_path / "cases").mkdir()
    (tmp_path / "cases.csv").write_text("id\nfrom-csv\n")
    (tmp_path / "cases" / "a.yaml").write_text("id: from-yaml\nfiles: [a.pdf]\n")
    (tmp_path / "cases" / "a.pdf").write_bytes(b"%PDF")
    (tmp_path / "cases" / "more.csv").write_text("id\nfrom-dir-csv\n")
    (tmp_path / "doc.txt").write_text("order")
    return tmp_path


class TestCaseCollector:
    def test_collects_files_directories_and_inline_cases_in_order(self, suite_dir):
        cases = CaseCollector(suite_dir).collect(["cases.csv", "cases", EvalCase(id="inline", files=["doc.txt"])])

        assert [c.id for c in cases] == ["from-csv", "from-yaml", "from-dir-csv", "inline"]
        assert cases[1].files == [(suite_dir / "cases" / "a.pdf").resolve()]
        assert cases[3].files == [(suite_dir / "doc.txt").resolve()]

    def test_a_single_path_is_accepted(self, suite_dir):
        assert [c.id for c in CaseCollector(suite_dir).collect("cases.csv")] == ["from-csv"]

    def test_a_duplicate_id_across_sources_names_both(self, suite_dir):
        (suite_dir / "again.csv").write_text("id\nfrom-yaml\n")

        with pytest.raises(DuplicateCaseError) as e:
            CaseCollector(suite_dir).collect(["cases", "again.csv"])

        assert e.value.case_id == "from-yaml"
        assert f"in {(suite_dir / 'cases' / 'a.yaml').resolve()} and in {(suite_dir / 'again.csv').resolve()}" in str(
            e.value
        )

    def test_a_suite_may_point_cases_at_its_own_directory(self, suite_dir):
        (suite_dir / "suite.yaml").write_text("agent: {id: 1}\n")

        assert [c.id for c in CaseCollector(suite_dir).collect(".")] == ["from-csv"]

    @pytest.mark.parametrize("entry, message", [("missing.csv", "No such"), ("doc.txt", "Unsupported")])
    def test_bad_paths_are_reported(self, suite_dir, entry, message):
        with pytest.raises(CaseSourceError, match=message):
            CaseCollector(suite_dir).collect(entry)

    def test_an_inline_case_with_a_missing_file_is_reported(self, suite_dir):
        with pytest.raises(CaseSourceError, match="nope.pdf"):
            CaseCollector(suite_dir).collect([EvalCase(id="x", files=["nope.pdf"])])
