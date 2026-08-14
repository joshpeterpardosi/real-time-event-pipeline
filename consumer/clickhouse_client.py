import time
import logging

logger = logging.getLogger(__name__)


class ClickHouseWriter:
    def __init__(self, client, table: str = "transactions", max_retries: int = 3, backoff_seconds: float = 1.0):
        self._client = client
        self._table = table
        self._max_retries = max_retries
        self._backoff_seconds = backoff_seconds
        self._buffer: list[dict] = []

    def insert_batch(self, rows: list[dict]) -> bool:
        for attempt in range(1, self._max_retries + 1):
            try:
                self._client.insert(
                    self._table,
                    [list(r.values()) for r in rows],
                    column_names=list(rows[0].keys()),
                )
                return True
            except Exception as exc:
                logger.warning("ClickHouse insert attempt %d/%d failed: %s", attempt, self._max_retries, exc)
                if attempt < self._max_retries:
                    time.sleep(self._backoff_seconds * attempt)
        logger.error("ClickHouse insert failed after %d attempts, buffering %d rows", self._max_retries, len(rows))
        self._buffer.extend(rows)
        return False

    @property
    def buffered_count(self) -> int:
        return len(self._buffer)
