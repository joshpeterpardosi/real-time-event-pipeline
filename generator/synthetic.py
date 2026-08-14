import random
import uuid
from datetime import datetime, timezone
from shared.schema import TransactionEvent

USERS = [f"user_{i}" for i in range(1, 51)]
MERCHANTS = ["Amazon", "Steam", "Uber", "Walmart", "Netflix"]
COUNTRIES = ["US", "GB", "DE", "SG", "BR"]
AMOUNT_FRAUD_FLOOR = 6000.0


def should_inject_fraud(sent: int, fraud_ratio: float) -> bool:
    if fraud_ratio <= 0:
        return False
    return sent % max(int(1 / fraud_ratio), 1) == 0


def generate_event(inject_fraud: bool = False) -> TransactionEvent:
    amount = round(random.uniform(AMOUNT_FRAUD_FLOOR, 9000), 2) if inject_fraud \
        else round(random.uniform(5, 500), 2)
    return TransactionEvent(
        transaction_id=str(uuid.uuid4()),
        user_id=random.choice(USERS),
        amount=amount,
        currency="USD",
        merchant=random.choice(MERCHANTS),
        country=random.choice(COUNTRIES),
        timestamp=datetime.now(timezone.utc).isoformat(),
        source="synthetic",
    )
