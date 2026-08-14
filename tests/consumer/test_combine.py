from consumer.combine import combine
from consumer import reasons


def test_no_rule_no_ml_is_not_fraud():
    is_fraud, reason, confidence = combine([], None)
    assert (is_fraud, reason, confidence) == (False, "", 0.0)


def test_rule_only_is_fraud_with_confidence_one():
    is_fraud, reason, confidence = combine([reasons.AMOUNT_THRESHOLD], None)
    assert is_fraud is True
    assert reason == reasons.AMOUNT_THRESHOLD
    assert confidence == 1.0


def test_ml_above_threshold_is_fraud_with_reason_ml():
    is_fraud, reason, confidence = combine([], 0.9)
    assert is_fraud is True
    assert reason == reasons.ML
    assert confidence == 0.9


def test_ml_below_threshold_alone_is_not_fraud():
    is_fraud, reason, confidence = combine([], 0.5)
    assert is_fraud is False
    assert reason == ""


def test_rule_and_ml_both_trigger_combines_reasons():
    is_fraud, reason, confidence = combine([reasons.VELOCITY], 0.9)
    assert is_fraud is True
    assert reason == f"{reasons.VELOCITY},{reasons.ML}"
    assert confidence == 0.9
