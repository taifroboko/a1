import asyncio
import pytest

from utils.request_manager import RequestManager


@pytest.mark.asyncio
async def test_queue_maxsize_and_shutdown():
    api_key = "test_key"
    async with RequestManager(api_key, queue_maxsize=1) as rm:
        worker = rm.worker
        assert worker.queue.maxsize == 1
        await asyncio.sleep(0)
    assert worker.task.done()
    assert worker.session is not None and worker.session.closed
    assert api_key not in RequestManager._workers


@pytest.mark.asyncio
async def test_shared_worker_lives_until_last_context():
    api_key = "shared_key"
    async with RequestManager(api_key) as rm1:
        async with RequestManager(api_key) as rm2:
            worker = rm1.worker
            # Both managers should share the same worker instance
            assert worker is rm2.worker
        # After exiting rm2, worker should still be active
        assert api_key in RequestManager._workers
        worker_entry = RequestManager._workers[api_key]
        assert worker_entry[0] is worker
        assert worker_entry[1] == 1

        async def dummy():
            return "ok"

        assert await rm1.call(dummy) == "ok"
    # After exiting rm1, worker should be shut down
    assert worker.task.done()
    assert api_key not in RequestManager._workers
