from unittest.mock import MagicMock, patch
from shared.schema import TransactionEvent


def _event():
    return TransactionEvent(
        transaction_id="t1", user_id="u1", amount=1.0, currency="USD",
        merchant="Amazon", country="US", timestamp="2026-08-14T00:00:00+00:00",
        source="synthetic",
    )


@patch("generator.producer.Producer")
def test_send_produces_with_user_id_as_key(mock_producer_cls):
    from generator.producer import EventProducer
    mock_instance = MagicMock()
    mock_producer_cls.return_value = mock_instance

    producer = EventProducer(bootstrap_servers="redpanda:9092")
    producer.send(_event())

    args, kwargs = mock_instance.produce.call_args
    assert args[0] == "transactions"
    assert kwargs["key"] == "u1"
    assert '"transaction_id": "t1"' in kwargs["value"]
