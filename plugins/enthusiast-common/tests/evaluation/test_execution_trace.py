import copy
import pickle
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

from enthusiast_common.evaluation.trace import Attempt, ExecutionTrace, LLMCall, MockCall, ToolCall, TraceRecorder, Turn


def _llm(run_id, parent=None, tokens=(10, 5)):
    return LLMCall(run_id=run_id, parent_run_id=parent, input_tokens=tokens[0], output_tokens=tokens[1])


class TestExecutionTrace:
    def test_a_call_reported_by_several_handlers_is_kept_once(self):
        trace = ExecutionTrace()

        assert trace.record_llm_call(_llm("r1")) is True
        assert trace.record_llm_call(_llm("r1")) is False
        assert trace.record_tool_call(ToolCall(run_id="t1", name="place_order")) is True
        assert trace.record_tool_call(ToolCall(run_id="t1", name="place_order")) is False
        assert (len(trace.llm_calls), len(trace.tool_calls)) == (1, 1)
        assert (trace.input_tokens, trace.output_tokens) == (10, 5)

    def test_a_trace_can_be_copied_and_pickled(self):
        trace = ExecutionTrace()
        trace.record_llm_call(_llm("r1"))

        for copied in (copy.deepcopy(trace), trace.model_copy(deep=True), pickle.loads(pickle.dumps(trace))):
            assert copied.llm_calls == trace.llm_calls

    def test_llm_calls_within_a_tool_are_found_by_parent(self):
        trace = ExecutionTrace()
        tool = ToolCall(run_id="t1", name="summarize")
        trace.record_tool_call(tool)
        trace.record_llm_call(_llm("agent-call"))
        trace.record_llm_call(_llm("nested", parent="t1"))

        assert [c.run_id for c in trace.llm_calls_within(tool)] == ["nested"]

    def test_llm_calls_within_a_tool_are_found_through_intermediate_runs(self):
        trace = ExecutionTrace()
        tool = ToolCall(run_id="t1", name="summarize")
        trace.record_run_parent("chain", "t1")
        trace.record_run_parent("t1", "agent")
        trace.record_llm_call(_llm("deep", parent="chain"))
        trace.record_llm_call(_llm("outside", parent="agent"))

        assert [c.run_id for c in trace.llm_calls_within(tool)] == ["deep"]

    def test_query_helpers(self):
        trace = ExecutionTrace()
        trace.record_tool_call(ToolCall(run_id="t1", name="place_order", error="RuntimeError: Out of stock"))
        trace.record_tool_call(ToolCall(run_id="t2", name="search"))
        trace.record_mock_call(MockCall(method="create_order_with_items", started_at=datetime.now()))
        trace.record_attempt(Attempt(number=1, response="{}", passed=False, failure_code="MISSING_SKU"))
        trace.record_attempt(Attempt(number=2, response="{}", passed=True))

        assert [c.run_id for c in trace.tool_calls_named("place_order")] == ["t1"]
        assert len(trace.mock_calls_to("create_order_with_items")) == 1
        assert trace.mock_calls_to("get_product_by_sku") == []
        assert trace.had_retry()
        assert trace.had_tool_error()
        assert trace.had_validator_failure("MISSING_SKU")
        assert not trace.had_validator_failure("OTHER")

    def test_calls_are_found_by_the_turn_that_made_them(self):
        trace = ExecutionTrace()
        for run_id in ("r1", "r2"):
            trace.record_llm_call(_llm(run_id))
        for run_id in ("t1", "t2"):
            trace.record_tool_call(ToolCall(run_id=run_id, name="search"))
        first = Turn(user_message="Hi", answer="Hello", llm_call_run_ids=["r1"])
        second = Turn(
            user_message="A kettle", answer="KTL-ELC", llm_call_run_ids=["r2"], tool_call_run_ids=["t1", "t2"]
        )
        trace.record_turn(first)
        trace.record_turn(second)

        assert trace.turns == [first, second]
        assert [c.run_id for c in trace.llm_calls_in(second)] == ["r2"]
        assert trace.tool_calls_in(first) == []
        assert [c.run_id for c in trace.tool_calls_in(second)] == ["t1", "t2"]

    def test_an_empty_trace_reports_nothing_happened(self):
        trace = ExecutionTrace()

        assert not trace.had_retry()
        assert not trace.had_tool_error()
        assert not trace.had_validator_failure()


class TestTraceRecorder:
    def test_recording_from_many_threads_loses_and_duplicates_nothing(self):
        recorder = TraceRecorder()
        run_ids = [f"r{i % 50}" for i in range(500)]

        with ThreadPoolExecutor(8) as pool:
            list(pool.map(lambda r: recorder.record_llm_call(_llm(r)), run_ids))

        assert sorted(c.run_id for c in recorder.trace.llm_calls) == sorted({*run_ids})

    def test_records_into_a_given_trace(self):
        trace = ExecutionTrace()
        recorder = TraceRecorder(trace)

        recorder.record_tool_call(ToolCall(run_id="t1", name="search"))
        recorder.record_mock_call(MockCall(method="m", started_at=datetime.now()))
        recorder.record_attempt(Attempt(number=1, response="{}", passed=True))

        assert (len(trace.tool_calls), len(trace.mock_calls), len(trace.attempts)) == (1, 1, 1)
