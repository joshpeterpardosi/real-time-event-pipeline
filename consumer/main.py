import logging
import time
from confluent_kafka import Consumer, Producer
import clickhouse_connect
from consumer.rules import RuleEngine
from consumer.ml_scorer import MLScorer
from consumer.clickhouse_client import ClickHouseWriter
from consumer.consumer import process_message

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BATCH_SIZE = 100
FLUSH_INTERVAL_SECONDS = 5


def main():
    ml_scorer = MLScorer(model_path="/app/ml/model.joblib")  # fails fast if missing
    rule_engine = RuleEngine()
    dead_letter_producer = Producer({"bootstrap.servers": "redpanda:9092"})
    ch_client = clickhouse_connect.get_client(host="clickhouse", port=8123)
    writer = ClickHouseWriter(ch_client)

    consumer = Consumer({
        "bootstrap.servers": "redpanda:9092",
        "group.id": "fraud-consumer",
        "enable.auto.commit": False,
        "auto.offset.reset": "earliest",
    })
    consumer.subscribe(["transactions"])

    batch, batch_messages = [], []
    last_flush = time.monotonic()

    while True:
        msg = consumer.poll(1.0)
        now = time.monotonic()
        if msg is not None and not msg.error():
            row = process_message(msg.value().decode("utf-8"), rule_engine, ml_scorer, now)
            if row is None:
                dead_letter_producer.produce("dead_letter", value=msg.value())
                dead_letter_producer.poll(0)
                consumer.commit(message=msg)
            else:
                batch.append(row)
                batch_messages.append(msg)

        if batch and (len(batch) >= BATCH_SIZE or now - last_flush >= FLUSH_INTERVAL_SECONDS):
            if writer.insert_batch(batch):
                consumer.commit(message=batch_messages[-1])
            batch, batch_messages = [], []
            last_flush = now


if __name__ == "__main__":
    main()
