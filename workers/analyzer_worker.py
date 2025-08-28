"""Worker entry point for processing contract analysis jobs from a queue.

This worker can be deployed on multiple machines and supervised by systems
like Kubernetes or ``systemd``.  Each worker pulls contract addresses from the
shared message queue and launches an ``A1Agent`` instance to analyse them.
"""

from __future__ import annotations

import asyncio
import os

from config.configuration_manager import ConfigurationManager
from core.queue import ContractQueue
from main import ContractProcessor


async def run_worker(concurrency: int = 3) -> None:
    """Run the analyzer worker."""

    config_manager = ConfigurationManager(os.environ.get("A1_CONFIG", ".env"))
    config = config_manager.get_config()

    queue_url = config.get("QUEUE_URL")
    queue_name = config.get("QUEUE_NAME", "contract_targets")

    queue = ContractQueue(queue_url, queue_name)
    await queue.connect()

    processor = ContractProcessor(config)
    await processor.initialize()

    await processor.process_queue(queue, concurrency)


def main() -> None:
    """Synchronous wrapper for running the worker."""

    concurrency = int(os.environ.get("A1_WORKER_CONCURRENCY", "3"))
    asyncio.run(run_worker(concurrency))


if __name__ == "__main__":
    main()

