import asyncio
import time
from typing import Any, Callable, Dict, Tuple
import aiohttp
import functools
import contextlib

class RequestManager:
    """Asynchronous request manager with rate limiting and batching.

    Handles request throttling on a per-key basis and executes queued
    requests in batches to avoid hitting external rate limits. Supports
    generic function calls in addition to standard HTTP requests.
    """

    _workers: Dict[str, "_RequestWorker"] = {}
    _worker_counts: Dict[str, int] = {}

    def __init__(self, api_key: str,
                 max_requests_per_second: int = 5,
                 max_batch_size: int = 5,
                 queue_maxsize: int = 0):
        self.api_key = api_key or "default"
        self.max_requests_per_second = max_requests_per_second
        self.max_batch_size = max_batch_size
        if self.api_key not in RequestManager._workers:
            RequestManager._workers[self.api_key] = _RequestWorker(
                max_requests_per_second, max_batch_size, maxsize=queue_maxsize
            )
            RequestManager._worker_counts[self.api_key] = 0
        RequestManager._worker_counts[self.api_key] += 1
        self.worker = RequestManager._workers[self.api_key]

    async def __aenter__(self) -> "RequestManager":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        count = RequestManager._worker_counts.get(self.api_key)
        if count is None:
            return None
        count -= 1
        if count <= 0:
            await self.worker.shutdown()
            RequestManager._workers.pop(self.api_key, None)
            RequestManager._worker_counts.pop(self.api_key, None)
        else:
            RequestManager._worker_counts[self.api_key] = count
        return None

    async def get(self, url: str, **kwargs) -> Any:
        return await self.worker.enqueue_http("GET", url, kwargs)

    async def post(self, url: str, **kwargs) -> Any:
        return await self.worker.enqueue_http("POST", url, kwargs)

    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute a generic callable respecting rate limits."""
        return await self.worker.enqueue_call(func, args, kwargs)


class _RequestWorker:
    """Background worker processing requests for a specific API key."""

    def __init__(self, max_rps: int, batch_size: int, maxsize: int = 0):
        self.queue: asyncio.Queue = asyncio.Queue(maxsize=maxsize)
        self.max_rps = max(1, max_rps)
        self.batch_size = max(1, batch_size)
        self.session: aiohttp.ClientSession | None = None
        self.task = asyncio.create_task(self._run())

    async def enqueue_http(self, method: str, url: str,
                           kwargs: Dict[str, Any]) -> Any:
        loop = asyncio.get_event_loop()
        fut = loop.create_future()
        await self.queue.put((fut, method.upper(), url, kwargs, False))
        return await fut

    async def enqueue_call(self, func: Callable,
                           args: Tuple[Any, ...],
                           kwargs: Dict[str, Any]) -> Any:
        loop = asyncio.get_event_loop()
        fut = loop.create_future()
        await self.queue.put((fut, func, args, kwargs, True))
        return await fut

    async def _fetch(self, session: aiohttp.ClientSession,
                     method: str, url: str, kwargs: Dict[str, Any]) -> Any:
        async with session.request(method, url, **kwargs) as resp:
            try:
                return await resp.json()
            except Exception:
                return await resp.text()

    async def _exec_call(self, func: Callable,
                         args: Tuple[Any, ...],
                         kwargs: Dict[str, Any]) -> Any:
        if asyncio.iscoroutinefunction(func):
            return await func(*args, **kwargs)
        loop = asyncio.get_running_loop()
        partial = functools.partial(func, *args, **kwargs)
        return await loop.run_in_executor(None, partial)

    async def _run(self) -> None:
        self.session = aiohttp.ClientSession()
        try:
            while True:
                fut, a, b, c, is_call = await self.queue.get()
                batch = [(fut, a, b, c, is_call)]
                try:
                    for _ in range(self.batch_size - 1):
                        batch.append(self.queue.get_nowait())
                except asyncio.QueueEmpty:
                    pass

                start = time.perf_counter()
                coros = []
                for fut, a, b, c, is_call in batch:
                    if is_call:
                        coros.append(self._exec_call(a, b, c))
                    else:
                        coros.append(self._fetch(self.session, a, b, c))

                results = await asyncio.gather(*coros, return_exceptions=True)
                for (fut, *_), result in zip(batch, results):
                    if isinstance(result, Exception):
                        fut.set_exception(result)
                    else:
                        fut.set_result(result)

                elapsed = time.perf_counter() - start
                min_interval = len(batch) / self.max_rps
                if elapsed < min_interval:
                    await asyncio.sleep(min_interval - elapsed)
        finally:
            await self.session.close()

    async def shutdown(self) -> None:
        if not self.task.done():
            self.task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self.task
        if self.session and not self.session.closed:
            await self.session.close()
