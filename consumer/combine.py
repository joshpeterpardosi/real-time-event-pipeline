from consumer import reasons as reason_constants
from shared.thresholds import ML_FRAUD_THRESHOLD


def combine(
    rule_reasons: list[str],
    ml_score: float | None,
    ml_threshold: float = ML_FRAUD_THRESHOLD,
) -> tuple[bool, str, float]:
    triggered = list(rule_reasons)
    ml_triggered = ml_score is not None and ml_score >= ml_threshold
    if ml_triggered:
        triggered.append(reason_constants.ML)

    is_fraud = bool(triggered)
    fraud_reason = ",".join(triggered)
    confidence = ml_score if ml_score is not None else (1.0 if rule_reasons else 0.0)
    return is_fraud, fraud_reason, confidence
