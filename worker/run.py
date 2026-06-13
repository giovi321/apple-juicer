from __future__ import annotations

import logging
import os

from rq import Queue, Worker

from core.queue import get_connection

logger = logging.getLogger(__name__)

QUEUE_NAMES = ["default"]


def main() -> None:
    """Boot an RQ worker on the default queue.

    Mirrors the docker-compose ``rq worker default`` command so the
    ``apple-juicer-worker`` console script and local development share a single
    startup path. Run with ``python -m worker.run`` or ``apple-juicer-worker``.
    """
    logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"))
    connection = get_connection()
    queues = [Queue(name, connection=connection) for name in QUEUE_NAMES]
    logger.info("Starting RQ worker on queues: %s", ", ".join(QUEUE_NAMES))
    worker = Worker(queues, connection=connection)
    worker.work(with_scheduler=True)


if __name__ == "__main__":
    main()
