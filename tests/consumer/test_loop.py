from unittest.mock import MagicMock
from shared.schema import TransactionEvent
from consumer.rules import RuleEngine
from consumer.loop import ConsumerLoop


class FakeMessage:
    def __init__(self, event: TransactionEvent = None, offset: int = 0, raw: bytes = None):
        self._event = event
        self.offset = offset
        self._raw = raw

    def value(self):
        if self._raw is not None:
            return self._raw
        return self._event.to_json().encode("utf-8")

    def error(self):
        return None


class FakeWriter:
    def __init__(self, results=None):
        self.calls = []
        self._results = list(results) if results is not None else [True]

    def insert_batch(self, rows):
        self.calls.append(list(rows))
        if len(self._results) > 1:
            return self._results.pop(0)
        return self._results[0]


class FakeDeadLetterProducer:
    def __init__(self):
        self.produced = []

    def produce(self, topic, value):
        self.produced.append((topic, value))

    def poll(self, timeout):
        pass


class FakeConsumer:
    def __init__(self):
        self.committed = []

    def commit(self, message):
        self.committed.append(message)


def _event(transaction_id="t1", user_id="u1", amount=10.0):
    return TransactionEvent(
        transaction_id=transaction_id, user_id=user_id, amount=amount, currency="USD",
        merchant="Amazon", country="US", timestamp="2026-08-14T00:00:00+00:00",
        source="synthetic",
    )


def _mock_ml():
    ml = MagicMock()
    ml.score.return_value = None
    return ml


def _loop(writer=None, batch_size=100, flush_interval_seconds=5.0):
    return ConsumerLoop(
        rule_engine=RuleEngine(),
        ml_scorer=_mock_ml(),
        writer=writer if writer is not None else FakeWriter(),
        dead_letter_producer=FakeDeadLetterProducer(),
        batch_size=batch_size,
        flush_interval_seconds=flush_interval_seconds,
    )


def test_valid_transaction_accumulates_without_flushing():
    writer = FakeWriter()
    loop = _loop(writer=writer, batch_size=100, flush_interval_seconds=5.0)
    consumer = FakeConsumer()
    msg = FakeMessage(_event(), offset=1)

    loop.handle(msg, now=0.0, consumer=consumer)

    assert writer.calls == []
    assert consumer.committed == []


def test_malformed_message_is_dead_lettered_and_committed_immediately():
    writer = FakeWriter()
    dead_letter = FakeDeadLetterProducer()
    loop = ConsumerLoop(
        rule_engine=RuleEngine(), ml_scorer=_mock_ml(), writer=writer,
        dead_letter_producer=dead_letter, batch_size=100, flush_interval_seconds=5.0,
    )
    consumer = FakeConsumer()
    msg = FakeMessage(raw=b"not-json", offset=7)

    loop.handle(msg, now=0.0, consumer=consumer)

    assert dead_letter.produced == [("dead_letter", b"not-json")]
    assert consumer.committed == [msg]
    assert writer.calls == []


def test_batch_size_reached_flushes_and_commits_last_offset():
    writer = FakeWriter(results=[True])
    loop = _loop(writer=writer, batch_size=2, flush_interval_seconds=5.0)
    consumer = FakeConsumer()
    msg1 = FakeMessage(_event(transaction_id="t1"), offset=1)
    msg2 = FakeMessage(_event(transaction_id="t2"), offset=2)

    loop.handle(msg1, now=0.0, consumer=consumer)
    loop.handle(msg2, now=0.1, consumer=consumer)

    assert len(writer.calls) == 1
    assert [r["transaction_id"] for r in writer.calls[0]] == ["t1", "t2"]
    assert consumer.committed == [msg2]


def test_insert_failure_keeps_pending_and_does_not_commit():
    writer = FakeWriter(results=[False])
    loop = _loop(writer=writer, batch_size=2, flush_interval_seconds=5.0)
    consumer = FakeConsumer()
    msg1 = FakeMessage(_event(transaction_id="t1"), offset=1)
    msg2 = FakeMessage(_event(transaction_id="t2"), offset=2)

    loop.handle(msg1, now=0.0, consumer=consumer)
    loop.handle(msg2, now=0.1, consumer=consumer)

    assert len(writer.calls) == 1
    assert consumer.committed == []


def test_failed_flush_retried_rows_merge_with_next_batch_and_commit_newest_offset():
    writer = FakeWriter(results=[False, True])
    loop = _loop(writer=writer, batch_size=2, flush_interval_seconds=5.0)
    consumer = FakeConsumer()
    msg1 = FakeMessage(_event(transaction_id="t1"), offset=1)
    msg2 = FakeMessage(_event(transaction_id="t2"), offset=2)
    msg3 = FakeMessage(_event(transaction_id="t3"), offset=3)

    loop.handle(msg1, now=0.0, consumer=consumer)
    loop.handle(msg2, now=0.1, consumer=consumer)  # flush attempt fails, t1+t2 stay pending
    loop.handle(msg3, now=0.2, consumer=consumer)  # flush attempt merges t1+t2+t3, succeeds

    assert len(writer.calls) == 2
    assert [r["transaction_id"] for r in writer.calls[1]] == ["t1", "t2", "t3"]
    assert consumer.committed == [msg3]


def test_idle_poll_with_no_message_still_flushes_on_elapsed_interval():
    writer = FakeWriter(results=[True])
    loop = _loop(writer=writer, batch_size=100, flush_interval_seconds=5.0)
    consumer = FakeConsumer()
    msg1 = FakeMessage(_event(transaction_id="t1"), offset=1)

    loop.handle(msg1, now=0.0, consumer=consumer)
    loop.handle(None, now=6.0, consumer=consumer)

    assert len(writer.calls) == 1
    assert [r["transaction_id"] for r in writer.calls[0]] == ["t1"]
    assert consumer.committed == [msg1]


def test_insert_failure_logs_warning_with_pending_count(caplog):
    writer = FakeWriter(results=[False])
    loop = _loop(writer=writer, batch_size=2, flush_interval_seconds=5.0)
    consumer = FakeConsumer()
    msg1 = FakeMessage(_event(transaction_id="t1"), offset=1)
    msg2 = FakeMessage(_event(transaction_id="t2"), offset=2)

    with caplog.at_level("WARNING", logger="consumer.loop"):
        loop.handle(msg1, now=0.0, consumer=consumer)
        loop.handle(msg2, now=0.1, consumer=consumer)

    assert any("2" in r.message and "pending" in r.message for r in caplog.records)


def test_flush_interval_elapsed_flushes_below_batch_size():
    writer = FakeWriter(results=[True])
    loop = _loop(writer=writer, batch_size=100, flush_interval_seconds=5.0)
    consumer = FakeConsumer()
    msg1 = FakeMessage(_event(transaction_id="t1"), offset=1)
    msg2 = FakeMessage(_event(transaction_id="t2"), offset=2)

    loop.handle(msg1, now=0.0, consumer=consumer)
    loop.handle(msg2, now=6.0, consumer=consumer)

    assert len(writer.calls) == 1
    assert [r["transaction_id"] for r in writer.calls[0]] == ["t1", "t2"]
    assert consumer.committed == [msg2]
