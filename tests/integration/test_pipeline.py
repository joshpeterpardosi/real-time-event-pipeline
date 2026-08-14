import time
import uuid
import pytest
import clickhouse_connect
from generator.producer import EventProducer
from shared.schema import TransactionEvent

pytestmark = pytest.mark.integration


def test_known_fraud_pattern_is_flagged_in_clickhouse():
    marker_user = f"itest_{uuid.uuid4().hex[:8]}"
    fraud_event = TransactionEvent(
        transaction_id=str(uuid.uuid4()), user_id=marker_user, amount=8000.0,
        currency="USD", merchant="Amazon", country="US",
        timestamp="2026-08-14T00:00:00+00:00", source="synthetic",
    )

    producer = EventProducer(bootstrap_servers="localhost:9092")
    producer.send(fraud_event)
    producer.flush()

    ch_client = clickhouse_connect.get_client(host="localhost", port=8123, username="default", password="localdev")
    deadline = time.monotonic() + 30
    row = None
    while time.monotonic() < deadline:
        result = ch_client.query(
            "SELECT is_fraud, fraud_reason FROM transactions WHERE user_id = {user_id:String}",
            parameters={"user_id": marker_user},
        )
        if result.result_rows:
            row = result.result_rows[0]
            break
        time.sleep(1)

    assert row is not None, "transaction did not land in ClickHouse within 30s"
    is_fraud, fraud_reason = row
    assert is_fraud == 1
    assert "rule:amount_threshold" in fraud_reason
