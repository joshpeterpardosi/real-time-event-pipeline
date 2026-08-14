from confluent_kafka import Producer
from shared.schema import TransactionEvent


class EventProducer:
    def __init__(self, bootstrap_servers: str, topic: str = "transactions"):
        self._producer = Producer({"bootstrap.servers": bootstrap_servers})
        self._topic = topic

    def send(self, event: TransactionEvent) -> None:
        self._producer.produce(self._topic, key=event.user_id, value=event.to_json())
        self._producer.poll(0)

    def flush(self) -> None:
        self._producer.flush()
