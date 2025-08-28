"""Message queue utilities for distributing contract analysis jobs.

This module provides a small abstraction over a message broker.  It supports
RabbitMQ via :mod:`aio_pika` when a broker URL is supplied and falls back to an
in-memory :class:`asyncio.Queue` for local testing.  Jobs consist of contract
addresses and their associated network identifiers.
"""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from typing import AsyncIterator, Optional

try:  # pragma: no cover - optional dependency
    import aio_pika
except Exception:  # pragma: no cover - library may not be installed
    aio_pika = None  # type: ignore


@dataclass
class QueueItem:
    """Simple container for contract analysis jobs."""

    address: str
    network: str = "ethereum"


class ContractQueue:
    """Abstraction over a message queue used to distribute analysis jobs.

    Parameters
    ----------
    url:
        Connection URL for the message broker.  If omitted, an in-memory queue
        is used which is suitable for tests or development environments.
    queue_name:
        Name of the queue inside the broker.
    """

    def __init__(self, url: Optional[str] = None, queue_name: str = "contract_targets"):
        self.url = url
        self.queue_name = queue_name
        self._connection = None
        self._channel = None
        self._queue = None
        self._local_queue: asyncio.Queue[QueueItem] = asyncio.Queue()

    async def connect(self) -> None:
        """Establish connection to the broker if a URL was supplied."""

        if self.url and aio_pika:
            self._connection = await aio_pika.connect_robust(self.url)
            self._channel = await self._connection.channel()
            self._queue = await self._channel.declare_queue(self.queue_name, durable=True)

    async def close(self) -> None:
        """Close any open broker connections."""

        if self._connection:
            await self._connection.close()
            self._connection = None

    async def enqueue(self, item: QueueItem) -> None:
        """Add a job to the queue."""

        if self._queue and aio_pika:
            body = json.dumps(item.__dict__).encode()
            message = aio_pika.Message(body=body)
            await self._channel.default_exchange.publish(message, routing_key=self.queue_name)
        else:
            await self._local_queue.put(item)

    async def dequeue(self) -> QueueItem:
        """Remove a job from the queue, waiting if necessary."""

        if self._queue and aio_pika:
            message = await self._queue.get()
            async with message.process():
                data = json.loads(message.body.decode())
                return QueueItem(**data)

        return await self._local_queue.get()

    async def consume(self) -> AsyncIterator[QueueItem]:
        """Iterate over jobs as they arrive."""

        while True:
            item = await self.dequeue()
            yield item


__all__ = ["QueueItem", "ContractQueue"]

