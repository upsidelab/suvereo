import pytest
from enthusiast_common.evaluation.metrics import MetricConfigError
from enthusiast_common.evaluation.metrics.llm import LLMClassify, LLMJudge
from enthusiast_common.evaluation.trace import ToolCall

from .contexts import run
from .scripted_judge import ScriptedJudge

CRITERIA = [
    {"name": "completeness", "description": "Every line item is ordered", "weight": 3},
    {"name": "no_invented_skus", "description": "No SKU absent from the document"},
]


def _judged(judge, **trace_fields):
    context = run(output={"order_id": "ORD-1"}, expected={"output": {"order_id": "ORD-1"}}, **trace_fields)
    context.judge = judge
    return context


class TestLLMJudge:
    def test_asks_each_criterion_separately_and_weights_the_scores(self):
        judge = ScriptedJudge('{"score": 1, "reasoning": "all there"}', '{"score": 0, "reasoning": "SKU-9 invented"}')

        result = LLMJudge({"criteria": CRITERIA}).measure(_judged(judge))

        assert result.value == 0.75
        assert result.components == {"completeness": 1.0, "no_invented_skus": 0.0}
        assert result.details["reasoning"]["no_invented_skus"] == "SKU-9 invented"
        assert len(judge.prompts) == 2 and "Every line item is ordered" in judge.prompts[0]

    def test_a_five_point_scale_is_normalised_and_samples_take_the_median(self):
        judge = ScriptedJudge('{"score": 5}', '{"score": 2}', '{"score": 4}')

        result = LLMJudge({"criteria": CRITERIA[:1], "scale": "1-5", "samples": 3}).measure(_judged(judge))

        assert result.value == 0.75

    def test_replies_wrapped_in_text_are_read(self):
        judge = ScriptedJudge('Sure! ```json\n{"score": 1, "reasoning": "ok"}\n```')

        assert LLMJudge({"criteria": CRITERIA[:1]}).measure(_judged(judge)).value == 1.0

    def test_the_score_object_is_found_among_other_braces(self):
        judge = ScriptedJudge('{"score": 1, "reasoning": "ok"} Note: I ignored {placeholders} and {"x": 2}.')

        assert LLMJudge({"criteria": CRITERIA[:1]}).measure(_judged(judge)).value == 1.0

    @pytest.mark.parametrize("reply", ["I think it is fine", '{"score": 7}', '{"verdict": 1}'])
    def test_an_unreadable_reply_is_not_scored(self, reply):
        result = LLMJudge({"criteria": CRITERIA[:1]}).measure(_judged(ScriptedJudge(reply)))

        assert result.value is None
        assert "completeness" in result.details["error"]

    def test_without_a_judge_nothing_is_measured(self):
        assert LLMJudge({"criteria": CRITERIA}).measure(run()).value is None

    def test_the_prompt_shows_only_the_chosen_material(self):
        judge = ScriptedJudge('{"score": 1}')
        context = _judged(
            judge, tool_calls=[ToolCall(run_id="t", name="place_order", args={"sku": "SKU-1"}, output="ok")]
        )

        LLMJudge({"criteria": CRITERIA[:1], "include": ["trace_summary"]}).measure(context)

        assert '## trace_summary\ntool place_order({"sku": "SKU-1"}) -> ok' in judge.prompts[0]
        assert "## output" not in judge.prompts[0]

    @pytest.mark.parametrize(
        "params", [{"criteria": []}, {"criteria": CRITERIA * 2}, {"criteria": CRITERIA, "include": ["everything"]}]
    )
    def test_invalid_params_fail_when_the_suite_loads(self, params):
        with pytest.raises(MetricConfigError):
            LLMJudge(params)


class TestLLMClassify:
    PARAMS = {"question": "Did the agent invent SKUs?", "labels": ["yes", "no"]}

    @pytest.mark.parametrize("reply, label", [("no", "no"), ("  Yes. ", "yes"), ("The answer is no.", "no")])
    def test_reads_the_label_from_the_reply(self, reply, label):
        assert LLMClassify(self.PARAMS).measure(_judged(ScriptedJudge(reply))).value == label

    @pytest.mark.parametrize("reply", ["maybe", "yes or no, hard to say"])
    def test_a_reply_without_exactly_one_label_is_not_classified(self, reply):
        result = LLMClassify(self.PARAMS).measure(_judged(ScriptedJudge(reply)))

        assert result.value is None
        assert result.details["reply"] == reply
