import pytest
from suvereo_common.evaluation.metrics import MetricConfigError, MetricContext
from suvereo_common.evaluation.metrics.llm import LLMClassify, LLMJudge
from suvereo_common.evaluation.suite import ConversationEvalCase
from suvereo_common.evaluation.trace import ExecutionTrace, ToolCall, Turn

from .contexts import mock_call, run
from .scripted_judge import ScriptedJudge

CRITERIA = [
    {"name": "completeness", "description": "Every line item is ordered", "weight": 3},
    {"name": "no_invented_skus", "description": "No SKU absent from the document"},
]
ANSWERED = [Turn(user_message="Hi", answer="Hello"), Turn(user_message="Bye", answer="Bye")]


def _chat(judge, expected=None):
    """A two-turn conversation: the first turn searched the catalog after a failed price lookup and answered in
    markdown, the second raised."""
    trace = ExecutionTrace(
        tool_calls=[
            ToolCall(run_id="t1", name="price_lookup", error="Timeout"),
            ToolCall(run_id="t2", name="product_search", output='[{"sku": "KTL-ELC", "price": 39}]'),
        ],
        turns=[
            Turn(
                user_message="I need a kettle",
                answer="## Kettles\n\nKTL-ELC, 39 EUR",
                tool_call_run_ids=["t1", "t2"],
            ),
            Turn(user_message="Cheaper?", error="RuntimeError: model down"),
        ],
        stop_reason="error",
        error="RuntimeError: model down",
    )
    case = ConversationEvalCase(id="c", user_messages=["I need a kettle", "Cheaper?"], expected=expected or {})
    return MetricContext(trace=trace, case=case, kind="conversation", judge=judge)


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
        assert result.binary_components is True
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

    def test_an_unreadable_criterion_keeps_the_scores_of_the_readable_ones(self):
        judge = ScriptedJudge('{"score": 1, "reasoning": "all there"}', "no idea")

        result = LLMJudge({"criteria": CRITERIA}).measure(_judged(judge))

        assert (result.value, result.components) == (None, {"completeness": 1.0})
        assert "no_invented_skus" in result.details["error"]
        assert result.details["reasoning"] == {"completeness": "all there"}

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

    def test_the_outcome_states_how_the_run_ended_and_which_mocks_it_called(self):
        judge = ScriptedJudge('{"score": 1}')
        context = run(success=False, failure_code="validation_failed")
        context.trace.execution_result.failure_summary = "No product matched"
        context.judge = judge

        LLMJudge({"criteria": CRITERIA[:1], "include": ["outcome"]}).measure(context)

        assert judge.prompts[0].endswith(
            "## outcome\nrun: failed (validation_failed): No product matched\n"
            "mock calls: none; the agent called no mocked external system"
        )

    @pytest.mark.parametrize(
        "turns, error, stop_reason, ended",
        [
            (ANSWERED, None, "done", "conversation of 2 turn(s), every turn answered; the user finished"),
            (ANSWERED, None, "gave_up", "conversation of 2 turn(s), every turn answered; the user gave up"),
            (
                ANSWERED,
                None,
                "max_turns",
                "conversation of 2 turn(s), every turn answered; cut off at the case's turn limit",
            ),
            (
                [*ANSWERED, Turn(user_message="More", error="RuntimeError: down")],
                "RuntimeError: down",
                "error",
                "crashed after 3 turn(s): RuntimeError: down",
            ),
            ([], None, "done", "ended before the first turn"),
        ],
    )
    def test_a_conversations_outcome_states_how_the_conversation_ended(self, turns, error, stop_reason, ended):
        judge = ScriptedJudge('{"score": 1}')
        trace = ExecutionTrace(turns=turns, error=error, stop_reason=stop_reason)
        context = MetricContext(
            trace=trace,
            case=ConversationEvalCase(id="c", user_messages=["Hi", "Bye"]),
            kind="conversation",
            judge=judge,
        )

        LLMJudge({"criteria": CRITERIA[:1], "include": ["outcome"]}).measure(context)

        assert f"## outcome\nrun: {ended}\n" in judge.prompts[0]

    def test_a_conversations_input_is_what_the_user_said_and_wanted(self):
        judge = ScriptedJudge('{"score": 1}')
        case = ConversationEvalCase(
            id="c", simulated_user={"class": "my.Simulator", "goal": "Get a kettle", "persona": "terse"}
        )
        trace = ExecutionTrace(turns=[Turn(user_message="kettle?", answer="KTL-ELC")])
        context = MetricContext(trace=trace, case=case, kind="conversation", judge=judge)

        LLMJudge({"criteria": CRITERIA[:1], "include": ["input"]}).measure(context)

        assert '"user_messages": [\n    "kettle?"\n  ]' in judge.prompts[0]
        assert '"goal": "Get a kettle"' in judge.prompts[0]
        assert '"input"' not in judge.prompts[0]

    def test_the_outcome_counts_the_calls_to_each_mocked_method(self):
        judge = ScriptedJudge('{"score": 1}')
        context = _judged(
            judge, mock_calls=[mock_call("create_order"), mock_call("create_order"), mock_call("get_url")]
        )

        LLMJudge({"criteria": CRITERIA[:1], "include": ["outcome"]}).measure(context)

        assert "run: succeeded\nmock calls: create_order ×2, get_url ×1" in judge.prompts[0]

    def test_the_judge_sees_the_outcome_output_and_expected_by_default(self):
        judge = ScriptedJudge('{"score": 1}')

        LLMJudge({"criteria": CRITERIA[:1]}).measure(_judged(judge))

        prompt = judge.prompts[0]
        assert prompt.index("## outcome") < prompt.index("## output") < prompt.index("## expected")
        assert "## transcript" not in prompt

    def test_a_conversations_judge_sees_the_outcome_transcript_and_expected_by_default(self):
        judge = ScriptedJudge('{"score": 1}')
        expected = {"outcome": "The user gets a kettle under 50 EUR"}

        LLMJudge({"criteria": CRITERIA[:1]}).measure(_chat(judge, expected))

        prompt = judge.prompts[0]
        assert prompt.index("## outcome") < prompt.index("## transcript") < prompt.index("## expected")
        assert "## output" not in prompt
        assert '"outcome": "The user gets a kettle under 50 EUR"' in prompt

    def test_the_transcript_shows_a_long_tool_result_in_full(self):
        judge = ScriptedJudge('{"score": 1}')
        products = "[" + ", ".join(f'{{"sku": "SKU-{n}"}}' for n in range(150)) + "]"
        trace = ExecutionTrace(
            tool_calls=[ToolCall(run_id="t1", name="product_search", output=products)],
            turns=[Turn(user_message="Kettles?", answer="SKU-149", tool_call_run_ids=["t1"])],
        )
        context = MetricContext(
            trace=trace, case=ConversationEvalCase(id="c", user_messages=["Kettles?"]), kind="conversation", judge=judge
        )

        LLMJudge({"criteria": CRITERIA[:1], "include": ["transcript"]}).measure(context)

        assert len(products) > 1000
        assert f"tool product_search returned:\n  {products}\n" in judge.prompts[0]

    def test_the_transcript_shows_each_turn_with_what_its_tools_returned_and_indents_what_was_said(self):
        judge = ScriptedJudge('{"score": 1}')

        LLMJudge({"criteria": CRITERIA[:1], "include": ["transcript"]}).measure(_chat(judge))

        assert judge.prompts[0].endswith(
            "## transcript\n"
            "turn 1\nuser:\n  I need a kettle\n"
            "tool price_lookup returned:\n  raised Timeout\n"
            'tool product_search returned:\n  [{"sku": "KTL-ELC", "price": 39}]\n'
            "agent:\n  ## Kettles\n\n  KTL-ELC, 39 EUR\n\n"
            "turn 2\nuser:\n  Cheaper?\nagent raised:\n  RuntimeError: model down"
        )

    @pytest.mark.parametrize("kind", ["execution", "conversation"])
    def test_a_run_that_raised_before_answering_is_not_judged(self, kind):
        judge = ScriptedJudge('{"score": 1}')
        trace = ExecutionTrace(turns=[Turn(user_message="Hi", error="RuntimeError: down")], error="RuntimeError: down")
        context = MetricContext(
            trace=trace, case=ConversationEvalCase(id="c", user_messages=["Hi"]), kind=kind, judge=judge
        )

        result = LLMJudge({"criteria": CRITERIA[:1]}).measure(context)

        assert (result.value, result.details["reason"]) == (
            None,
            "the run raised before it answered, so there is nothing to judge",
        )
        assert judge.prompts == []

    @pytest.mark.parametrize(
        "params, kind, supported",
        [
            ({}, "execution", True),
            ({}, "conversation", True),
            ({"include": ["outcome", "transcript"]}, "conversation", True),
            ({"include": ["outcome", "transcript"]}, "execution", False),
        ],
    )
    def test_a_transcript_can_only_be_shown_for_a_conversation(self, params, kind, supported):
        assert LLMJudge({"criteria": CRITERIA[:1], **params}).supports(kind) is supported

    def test_a_custom_score_range_is_normalised(self):
        judge = ScriptedJudge('{"score": 7}')

        result = LLMJudge({"criteria": CRITERIA[:1], "scale": {"min": 0, "max": 10}}).measure(_judged(judge))

        assert result.value == pytest.approx(0.7)
        assert "from 0 (not met at all) to 10 (fully met)" in judge.prompts[0]

    def test_a_custom_prompt_and_judge_model_are_used(self, tmp_path):
        (tmp_path / "judge.txt").write_text("Grade {name} ({description}) {scale}.\n{material}")
        params = {
            "criteria": CRITERIA[:1],
            "prompt_file": "judge.txt",
            "judge": {"provider": "OpenAI", "model": "gpt-4.1"},
        }
        judge = ScriptedJudge('{"score": 1}')

        LLMJudge(params, base_dir=tmp_path).measure(_judged(judge))

        assert judge.prompts[0].startswith("Grade completeness (Every line item is ordered) 0 (not met) or 1 (met).")
        assert judge.models[0].model == "gpt-4.1"

    @pytest.mark.parametrize(
        "params",
        [
            {"criteria": []},
            {"criteria": CRITERIA * 2},
            {"criteria": CRITERIA, "include": ["everything"]},
            {"criteria": CRITERIA, "scale": {"min": 5, "max": 5}},
            {"criteria": CRITERIA, "prompt": "Grade {criterion}: {material}"},
            {"criteria": CRITERIA, "prompt": "Grade {name} without the run"},
            {"criteria": CRITERIA, "prompt": 'Reply {"score": 1} {material}'},
            {"criteria": CRITERIA, "prompt": "{material}", "prompt_file": "judge.txt"},
            {"criteria": CRITERIA, "prompt_file": "missing.txt"},
        ],
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

    def test_a_conversation_is_classified_from_its_outcome_and_transcript_by_default(self):
        judge = ScriptedJudge("no")

        LLMClassify(self.PARAMS).measure(_chat(judge))

        prompt = judge.prompts[0]
        assert prompt.index("## outcome") < prompt.index("## transcript")
        assert "## output" not in prompt

    def test_a_transcript_can_only_be_shown_for_a_conversation(self):
        classify = LLMClassify({**self.PARAMS, "include": ["transcript"]})

        assert (classify.supports("conversation"), classify.supports("execution")) == (True, False)

    def test_a_custom_prompt_and_judge_model_are_used(self):
        params = {
            **self.PARAMS,
            "prompt": "Q: {question} A: {labels}\n{material}",
            "judge": {"provider": "X", "model": "m"},
        }
        judge = ScriptedJudge("no")

        assert LLMClassify(params).measure(_judged(judge)).value == "no"
        assert judge.prompts[0].startswith("Q: Did the agent invent SKUs? A: yes, no")
        assert judge.models[0].model == "m"
