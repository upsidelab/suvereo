import asyncio
from concurrent.futures import ThreadPoolExecutor
from contextvars import copy_context

from enthusiast_common.evaluation.trace import TraceRecorder

from agent.evaluation.run_context import EvalRunContext


class TestEvalRunContext:
    def test_there_is_no_current_run_outside_an_evaluation(self):
        assert EvalRunContext.current() is None

    def test_activate_makes_it_current_for_the_block_only(self):
        context = EvalRunContext(TraceRecorder())

        with context.activate():
            assert EvalRunContext.current() is context
        assert EvalRunContext.current() is None

    def test_it_reaches_worker_threads_and_event_loops(self):
        context = EvalRunContext(TraceRecorder())

        with context.activate():
            in_thread = asyncio.run(asyncio.to_thread(EvalRunContext.current))
            in_loop = asyncio.run(self._current())
            with ThreadPoolExecutor(1) as pool:
                in_pool = pool.submit(copy_context().run, EvalRunContext.current).result()

        assert in_thread is in_loop is in_pool is context

    @staticmethod
    async def _current():
        return EvalRunContext.current()
