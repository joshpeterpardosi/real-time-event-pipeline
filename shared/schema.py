from dataclasses import dataclass, asdict
from typing import Optional
import json


@dataclass
class TransactionEvent:
    transaction_id: str
    user_id: str
    amount: float
    currency: str
    merchant: str
    country: str
    timestamp: str
    source: str
    features: Optional[list] = None

    def to_json(self) -> str:
        return json.dumps(asdict(self))

    @staticmethod
    def from_json(raw: str) -> "TransactionEvent":
        return TransactionEvent(**json.loads(raw))
