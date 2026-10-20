from enthusiast_common.evaluation.trace import TraceRecorder
from langchain_core.documents import Document
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage
from langchain_core.retrievers import BaseRetriever
from langchain_core.runnables import RunnableLambda
from langchain_core.tools import tool

from agent.evaluation.run_context import EvalRunContext
from agent.evaluation.trace_callback_handler import TraceCallbackHandler


def _reply(**fields):
    defaults = {
        "content": "ok",
        "usage_metadata": {
            "input_tokens": 120,
            "output_tokens": 30,
            "total_tokens": 150,
            "input_token_details": {"cache_read": 20},
            "output_token_details": {"reasoning": 5},
        },
        "response_metadata": {"model_name": "gpt-4o-mini-2024-07-18", "finish_reason": "stop"},
    }
    return AIMessage(**{**defaults, **fields})


@tool
def lookup_sku(product: str) -> str:
    """Return the SKU for a product."""
    return "SKU-1"


@tool
def place_order(sku: str) -> str:
    """Place an order."""
    raise RuntimeError("Out of stock")


class TestTraceCallbackHandler:
    def test_records_an_llm_call_with_usage_model_and_timing(self):
        recorder = TraceRecorder()
        model = GenericFakeChatModel(
            messages=iter([_reply(tool_calls=[{"name": "lookup_sku", "args": {"product": "mug"}, "id": "1"}])])
        )

        model.invoke("hi", config={"callbacks": [TraceCallbackHandler(recorder)]})

        [call] = recorder.trace.llm_calls
        assert (call.input_tokens, call.cached_input_tokens, call.output_tokens, call.reasoning_tokens) == (
            120,
            20,
            30,
            5,
        )
        assert (call.model, call.finish_reason) == ("gpt-4o-mini-2024-07-18", "stop")
        assert call.requested_tool_calls == [{"name": "lookup_sku", "args": {"product": "mug"}}]
        assert call.duration_s is not None

    def test_records_tool_calls_and_their_errors(self):
        recorder = TraceRecorder()
        handler = TraceCallbackHandler(recorder)

        lookup_sku.invoke({"product": "mug"}, config={"callbacks": [handler]})
        try:
            place_order.invoke({"sku": "SKU-1"}, config={"callbacks": [handler]})
        except RuntimeError:
            pass

        lookup, order = recorder.trace.tool_calls
        assert (lookup.name, lookup.args, lookup.output) == ("lookup_sku", {"product": "mug"}, "SKU-1")
        assert (order.name, order.error) == ("place_order", "RuntimeError: Out of stock")

    def test_writes_to_the_current_run_when_given_no_recorder(self):
        context = EvalRunContext(TraceRecorder())
        model = GenericFakeChatModel(messages=iter([_reply()]))

        with context.activate():
            model.invoke("hi", config={"callbacks": [TraceCallbackHandler()]})

        assert len(context.recorder.trace.llm_calls) == 1

    def test_is_a_no_op_outside_an_evaluation_and_keeps_nothing(self):
        handler = TraceCallbackHandler()
        model = GenericFakeChatModel(messages=iter([_reply()]))

        model.invoke("hi", config={"callbacks": [handler]})

        assert handler._llm_starts == {}

    def test_one_call_seen_by_two_handlers_is_recorded_once(self):
        context = EvalRunContext(TraceRecorder())
        model = GenericFakeChatModel(messages=iter([_reply()]), callbacks=[TraceCallbackHandler()])

        with context.activate():
            model.invoke("hi", config={"callbacks": [TraceCallbackHandler()]})

        assert len(context.recorder.trace.llm_calls) == 1

    def test_a_reply_without_usage_is_marked_unreported_and_cache_writes_are_kept(self):
        recorder = TraceRecorder()
        silent = GenericFakeChatModel(messages=iter([AIMessage(content="ok")]))
        cached = GenericFakeChatModel(
            messages=iter(
                [
                    _reply(
                        usage_metadata={
                            "input_tokens": 100,
                            "output_tokens": 5,
                            "total_tokens": 105,
                            "input_token_details": {
                                "cache_creation": 0,
                                "ephemeral_5m_input_tokens": 40,
                                "ephemeral_1h_input_tokens": 20,
                            },
                        }
                    )
                ]
            )
        )

        silent.invoke("hi", config={"callbacks": [TraceCallbackHandler(recorder)]})
        cached.invoke("hi", config={"callbacks": [TraceCallbackHandler(recorder)]})

        unreported, written = recorder.trace.llm_calls
        assert (unreported.usage_reported, unreported.input_tokens) == (False, 0)
        assert (written.usage_reported, written.cache_write_5m_input_tokens, written.cache_write_1h_input_tokens) == (
            True,
            40,
            20,
        )

    def test_an_llm_call_inside_a_chain_inside_a_tool_counts_as_within_the_tool(self):
        recorder = TraceRecorder()
        model = GenericFakeChatModel(messages=iter([_reply()]))
        chain = RunnableLambda(lambda text: text) | model

        @tool
        def summarize(text: str) -> str:
            """Summarize a text."""
            return chain.invoke(text).content

        summarize.invoke({"text": "long"}, config={"callbacks": [TraceCallbackHandler(recorder)]})

        [tool_call] = recorder.trace.tool_calls
        [llm_call] = recorder.trace.llm_calls
        assert llm_call.parent_run_id != tool_call.run_id
        assert recorder.trace.llm_calls_within(tool_call) == [llm_call]

    def test_an_llm_call_made_by_a_retriever_inside_a_tool_counts_as_within_the_tool(self):
        recorder = TraceRecorder()
        model = GenericFakeChatModel(messages=iter([_reply(content="rewritten")]))

        class RewritingRetriever(BaseRetriever):
            def _get_relevant_documents(self, query, *, run_manager):
                text = model.invoke(query, config={"callbacks": run_manager.get_child()}).content
                return [Document(page_content=text)]

        @tool
        def search(query: str) -> str:
            """Search the docs."""
            return RewritingRetriever().invoke(query)[0].page_content

        search.invoke({"query": "mugs"}, config={"callbacks": [TraceCallbackHandler(recorder)]})

        [tool_call] = recorder.trace.tool_calls
        assert [c.run_id for c in recorder.trace.llm_calls_within(tool_call)] == [recorder.trace.llm_calls[0].run_id]
