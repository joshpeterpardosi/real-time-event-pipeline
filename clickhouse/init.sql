-- Column order must match ClickHouseWriter.COLUMN_NAMES in consumer/clickhouse_client.py
-- (checked by tests/consumer/test_clickhouse_client.py::test_column_names_match_clickhouse_init_sql_schema)
CREATE TABLE IF NOT EXISTS transactions (
    transaction_id String,
    user_id String,
    amount Float64,
    currency String,
    merchant String,
    country String,
    event_timestamp String,
    source String,
    is_fraud UInt8,
    fraud_reason String,
    confidence_score Float64,
    ingested_at DateTime DEFAULT now()
) ENGINE = MergeTree()
ORDER BY (ingested_at, transaction_id);
