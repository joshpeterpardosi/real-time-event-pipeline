import csv
import uuid
from datetime import datetime, timezone
from typing import Iterator
from shared.schema import TransactionEvent


def row_to_event(row: dict) -> TransactionEvent:
    # Class (ground truth) intentionally dropped — training reads the CSV
    # directly instead, so the live stream never leaks the answer.
    features = [round(float(row[f"V{i}"]), 4) for i in range(1, 29)]
    return TransactionEvent(
        transaction_id=str(uuid.uuid4()),
        user_id=f"kaggle_{row['Time']}",
        amount=float(row["Amount"]),
        currency="USD",
        merchant="unknown",
        country="US",
        timestamp=datetime.now(timezone.utc).isoformat(),
        source="replay",
        features=features,
    )


def replay_csv(path: str) -> Iterator[TransactionEvent]:
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            yield row_to_event(row)
