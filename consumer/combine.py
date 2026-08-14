def combine(rule_reasons: list[str], ml_score: float | None, ml_threshold: float = 0.7) -> tuple[bool, str, float]:
    reasons = list(rule_reasons)
    ml_triggered = ml_score is not None and ml_score >= ml_threshold
    if ml_triggered:
        reasons.append("ml")

    is_fraud = bool(reasons)
    fraud_reason = ",".join(reasons)
    confidence = ml_score if ml_score is not None else (1.0 if rule_reasons else 0.0)
    return is_fraud, fraud_reason, confidence
