import logging
import time
from confluent_kafka import Consumer, Producer
import clickhouse_connect
from consumer.rules import RuleEngine
from consumer.ml_scorer import MLScorer
from consumer.clickhouse_client import ClickHouseWriter
from consumer.loop import ConsumerLoop

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BATCH_SIZE = 100
FLUSH_INTERVAL_SECONDS = 5


def main():
    ml_scorer = MLScorer(model_path="/app/ml/model.joblib")  # fails fast if missing
    rule_engine = RuleEngine()
    dead_letter_producer = Producer({"bootstrap.servers": "redpanda:9092"})
    ch_client = clickhouse_connect.get_client(host="clickhouse", port=8123, username="default", password="localdev")
    writer = ClickHouseWriter(ch_client)

    consumer = Consumer({
        "bootstrap.servers": "redpanda:9092",
        "group.id": "fraud-consumer",
        "enable.auto.commit": False,
        "auto.offset.reset": "earliest",
    })
    consumer.subscribe(["transactions"])

    loop = ConsumerLoop(
        rule_engine=rule_engine,
        ml_scorer=ml_scorer,
        writer=writer,
        dead_letter_producer=dead_letter_producer,
        batch_size=BATCH_SIZE,
        flush_interval_seconds=FLUSH_INTERVAL_SECONDS,
    )

    while True:
        msg = consumer.poll(1.0)
        usable_msg = msg if (msg is not None and not msg.error()) else None
        loop.handle(usable_msg, time.monotonic(), consumer)


if __name__ == "__main__":
    main()
