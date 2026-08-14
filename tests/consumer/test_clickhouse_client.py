import re
from pathlib import Path
from unittest.mock import MagicMock, patch
from consumer.clickhouse_client import ClickHouseWriter

INIT_SQL_PATH = Path(__file__).resolve().parents[2] / "clickhouse" / "init.sql"


def _ddl_column_names() -> list[str]:
    sql = INIT_SQL_PATH.read_text()
    body = re.search(r"CREATE TABLE.*?\((.*)\)\s*ENGINE", sql, re.DOTALL).group(1)
    return [line.strip().split()[0] for line in body.strip().splitlines()]


def _row(transaction_id="t1", amount=1.0):
    return {
        "transaction_id": transaction_id, "user_id": "u1", "amount": amount, "currency": "USD",
        "merchant": "Amazon", "country": "US", "event_timestamp": "2026-08-14T00:00:00+00:00",
        "source": "synthetic", "is_fraud": 0, "fraud_reason": "", "confidence_score": 0.0,
    }


def _rows():
    return [_row()]


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


def test_insert_batch_maps_rows_by_column_name_regardless_of_dict_key_order():
    mock_client = MagicMock()
    writer = ClickHouseWriter(mock_client)
    row1 = _row(transaction_id="t1", amount=1.0)
    row2 = dict(reversed(list(_row(transaction_id="t2", amount=2.0).items())))

    writer.insert_batch([row1, row2])

    _, args, kwargs = mock_client.insert.mock_calls[0]
    _table, values = args
    assert kwargs["column_names"] == ClickHouseWriter.COLUMN_NAMES
    assert values == [
        [row1[c] for c in ClickHouseWriter.COLUMN_NAMES],
        [row2[c] for c in ClickHouseWriter.COLUMN_NAMES],
    ]


def test_column_names_match_clickhouse_init_sql_schema():
    ddl_columns = _ddl_column_names()
    assert ddl_columns == ClickHouseWriter.COLUMN_NAMES + ["ingested_at"]
