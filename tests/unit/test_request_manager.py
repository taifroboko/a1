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
