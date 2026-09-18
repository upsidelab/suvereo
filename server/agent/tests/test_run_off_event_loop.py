import asyncio
import threading
from unittest.mock import patch

import pytest
from enthusiast_common.utils import run_off_event_loop


class TestRunOffEventLoop:
    """Sync ORM work is pushed onto a worker thread, and Django keeps connections thread-local.

    Nothing closes those connections for a thread the event loop borrowed, so without an explicit
    release each conversation turn would open a fresh database connection and leave it to garbage
    collection. These pin down that the release happens and that results still come back.
    """

    def test_runs_the_callable_off_the_event_loop_thread(self):
        loop_thread = threading.current_thread().name

        async def main():
            return await run_off_event_loop(lambda: threading.current_thread().name)

        assert asyncio.run(main()) != loop_thread

    def test_returns_the_result_and_passes_arguments_through(self):
        async def main():
            return await run_off_event_loop(lambda a, b: a + b, 2, 3)

        assert asyncio.run(main()) == 5

    @patch("django.db.connections.close_all")
    def test_releases_database_connections_afterwards(self, mock_close_all):
        async def main():
            return await run_off_event_loop(lambda: "done")

        assert asyncio.run(main()) == "done"
        mock_close_all.assert_called_once()

    @patch("django.db.connections.close_all")
    def test_releases_database_connections_even_when_the_callable_raises(self, mock_close_all):
        def boom():
            raise ValueError("nope")

        async def main():
            return await run_off_event_loop(boom)

        with pytest.raises(ValueError):
            asyncio.run(main())
        mock_close_all.assert_called_once()
