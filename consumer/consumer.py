import json
import logging
from shared.schema import TransactionEvent
from consumer.rules import RuleEngine
from consumer.ml_scorer import MLScorer
from consumer.combine import combine

logger = logging.getLogger(__name__)


def process_message(raw_value: str, rule_engine: RuleEngine, ml_scorer: MLScorer, now_epoch: float) -> dict | None:
    try:
        event = TransactionEvent.from_json(raw_value)
    except (json.JSONDecodeError, TypeError, KeyError) as exc:
        logger.warning("malformed event, routing to dead_letter: %s", exc)
        return None

    rule_reasons = rule_engine.evaluate(event, now_epoch)
    ml_score = ml_scorer.score(event)
    is_fraud, fraud_reason, confidence = combine(rule_reasons, ml_score)

    return {
        "transaction_id": event.transaction_id,
        "user_id": event.user_id,
        "amount": event.amount,
        "currency": event.currency,
        "merchant": event.merchant,
        "country": event.country,
        "event_timestamp": event.timestamp,
        "source": event.source,
        "is_fraud": int(is_fraud),
        "fraud_reason": fraud_reason,
        "confidence_score": confidence,
    }
