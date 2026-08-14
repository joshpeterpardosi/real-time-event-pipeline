import time
import logging

logger = logging.getLogger(__name__)


class ClickHouseWriter:
    # Must match the transactions table schema in clickhouse/init.sql (minus ingested_at,
    # which has a DB-side default). Checked by
    # tests/consumer/test_clickhouse_client.py::test_column_names_match_clickhouse_init_sql_schema
    COLUMN_NAMES = [
        "transaction_id", "user_id", "amount", "currency", "merchant", "country",
        "event_timestamp", "source", "is_fraud", "fraud_reason", "confidence_score",
    ]

    def __init__(self, client, table: str = "transactions", max_retries: int = 3, backoff_seconds: float = 1.0):
        self._client = client
        self._table = table
        self._max_retries = max_retries
        self._backoff_seconds = backoff_seconds

    def insert_batch(self, rows: list[dict]) -> bool:
        for attempt in range(1, self._max_retries + 1):
            try:
                self._client.insert(
                    self._table,
                    [[row[c] for c in self.COLUMN_NAMES] for row in rows],
                    column_names=self.COLUMN_NAMES,
                )
                return True
            except Exception as exc:
                logger.warning("ClickHouse insert attempt %d/%d failed: %s", attempt, self._max_retries, exc)
                if attempt < self._max_retries:
                    time.sleep(self._backoff_seconds * attempt)
        logger.error("ClickHouse insert failed after %d attempts", self._max_retries)
        return False
