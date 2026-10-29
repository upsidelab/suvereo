import pytest
from enthusiast_common.evaluation.errors import EvalSuiteError
from enthusiast_common.evaluation.suite import AgenticExecutionEvalCase

from agent.evaluation.suite_selection import SuiteSelection

from .suite_reports import loaded_suite

CASES = [
    AgenticExecutionEvalCase(id="ada", tags=["vip"]),
    AgenticExecutionEvalCase(id="bob", tags=["bulk"]),
    AgenticExecutionEvalCase(id="cy"),
]
VARIANTS = [{"name": "v2", "agent_config": {"x": 1}}, {"name": "v3", "agent_config": {"x": 2}}]


def _suite(tmp_path):
    return loaded_suite(tmp_path, cases=CASES, variants=VARIANTS)


class TestSuiteSelection:
    def test_an_empty_selection_keeps_the_suite(self, tmp_path):
        loaded = _suite(tmp_path)

        assert SuiteSelection().apply(loaded) == loaded

    def test_models_are_picked_by_label_or_added_as_provider_and_model(self, tmp_path):
        selected = SuiteSelection(models=["gpt", "Anthropic:claude-sonnet-5-5", "gpt"]).apply(_suite(tmp_path))

        assert [(m.provider, m.model) for m in selected.suite.models] == [
            ("OpenAI", "gpt-4.1"),
            ("Anthropic", "claude-sonnet-5-5"),
        ]

    def test_a_model_that_is_neither_a_label_nor_provider_and_model_is_refused(self, tmp_path):
        with pytest.raises(EvalSuiteError, match="neither a suite model"):
            SuiteSelection(models=["claude"]).apply(_suite(tmp_path))

    def test_variants_are_narrowed_by_name(self, tmp_path):
        selected = SuiteSelection(variants=["v3"]).apply(_suite(tmp_path))

        assert [v.name for v in selected.suite.variants] == ["v3"]

    def test_an_unknown_variant_is_refused(self, tmp_path):
        with pytest.raises(EvalSuiteError, match="No variant"):
            SuiteSelection(variants=["v9"]).apply(_suite(tmp_path))

    def test_a_prompt_file_becomes_a_variant_named_after_it(self, tmp_path):
        prompt = tmp_path / "terse.txt"

        selected = SuiteSelection(variants=["v2"], prompt_file=prompt).apply(_suite(tmp_path))

        assert [(v.name, v.system_prompt_file) for v in selected.suite.variants] == [
            ("v2", None),
            ("terse", str(prompt.resolve())),
        ]

    @pytest.mark.parametrize("file_name", ["v2.txt", "default.txt"])
    def test_a_prompt_file_named_like_a_variant_is_refused(self, tmp_path, file_name):
        with pytest.raises(EvalSuiteError, match="named like an existing variant"):
            SuiteSelection(prompt_file=tmp_path / file_name).apply(_suite(tmp_path))

    def test_cases_are_narrowed_by_id_and_tag(self, tmp_path):
        selected = SuiteSelection(case_ids=["ada", "bob"], tags=["bulk"]).apply(_suite(tmp_path))

        assert [case.id for case in selected.cases] == ["bob"]

    def test_an_unknown_case_id_is_refused(self, tmp_path):
        with pytest.raises(EvalSuiteError, match="No case"):
            SuiteSelection(case_ids=["zed"]).apply(_suite(tmp_path))

    def test_a_selection_matching_no_case_is_refused(self, tmp_path):
        with pytest.raises(EvalSuiteError, match="No case matches"):
            SuiteSelection(tags=["none"]).apply(_suite(tmp_path))

    def test_repeats_override_the_suites(self, tmp_path):
        assert SuiteSelection(repeats=3).apply(_suite(tmp_path)).suite.repeats == 3
