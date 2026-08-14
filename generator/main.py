import argparse
import time
from generator.producer import EventProducer
from generator.synthetic import generate_event, should_inject_fraud
from generator.replay import replay_csv


def run_synthetic(producer: EventProducer, rate_per_sec: float, fraud_ratio: float, count: int | None):
    sent = 0
    while count is None or sent < count:
        inject = should_inject_fraud(sent, fraud_ratio)
        producer.send(generate_event(inject_fraud=inject))
        sent += 1
        time.sleep(1 / rate_per_sec)
    producer.flush()


def run_replay(producer: EventProducer, csv_path: str):
    for event in replay_csv(csv_path):
        producer.send(event)
    producer.flush()


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="mode", required=True)

    synth = sub.add_parser("synthetic")
    synth.add_argument("--rate", type=float, default=5.0)
    synth.add_argument("--fraud-ratio", type=float, default=0.05)
    synth.add_argument("--count", type=int, default=None)

    replay = sub.add_parser("replay")
    replay.add_argument("--csv", required=True)

    args = parser.parse_args()
    producer = EventProducer(bootstrap_servers="redpanda:9092")

    if args.mode == "synthetic":
        run_synthetic(producer, args.rate, args.fraud_ratio, args.count)
    else:
        run_replay(producer, args.csv)


if __name__ == "__main__":
    main()
