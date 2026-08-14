from unittest.mock import MagicMock, patch
from consumer.clickhouse_client import ClickHouseWriter


def _rows():
    return [{"transaction_id": "t1", "amount": 1.0}]


def test_insert_batch_succeeds_on_first_try():
    mock_client = MagicMock()
    writer = ClickHouseWriter(mock_client)

    ok = writer.insert_batch(_rows())

    assert ok is True
    mock_client.insert.assert_called_once()


@patch("consumer.clickhouse_client.time.sleep")
def test_insert_batch_retries_three_times_then_gives_up(mock_sleep):
    mock_client = MagicMock()
    mock_client.insert.side_effect = RuntimeError("connection refused")
    writer = ClickHouseWriter(mock_client, max_retries=3, backoff_seconds=1.0)

    ok = writer.insert_batch(_rows())

    assert ok is False
    assert mock_client.insert.call_count == 3
