import logging
from consumer.consumer import process_message

logger = logging.getLogger(__name__)


class ConsumerLoop:
    def __init__(self, rule_engine, ml_scorer, writer, dead_letter_producer,
                 batch_size: int = 100, flush_interval_seconds: float = 5.0):
        self._rule_engine = rule_engine
        self._ml_scorer = ml_scorer
        self._writer = writer
        self._dead_letter_producer = dead_letter_producer
        self._batch_size = batch_size
        self._flush_interval_seconds = flush_interval_seconds
        self._pending: list[tuple[dict, object]] = []
        self._last_flush = None

    def handle(self, msg, now: float, consumer) -> None:
        if self._last_flush is None:
            self._last_flush = now

        if msg is not None:
            row = process_message(msg.value().decode("utf-8"), self._rule_engine, self._ml_scorer, now)
            if row is None:
                self._dead_letter_producer.produce("dead_letter", value=msg.value())
                self._dead_letter_producer.poll(0)
                consumer.commit(message=msg)
            else:
                self._pending.append((row, msg))

        if self._pending and (
            len(self._pending) >= self._batch_size
            or now - self._last_flush >= self._flush_interval_seconds
        ):
            rows = [r for r, _ in self._pending]
            if self._writer.insert_batch(rows):
                consumer.commit(message=self._pending[-1][1])
                self._pending = []
            else:
                logger.warning("ClickHouse insert failed, %d rows pending retry", len(self._pending))
            self._last_flush = now
