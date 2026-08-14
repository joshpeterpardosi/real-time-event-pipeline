from consumer.combine import combine


def test_no_rule_no_ml_is_not_fraud():
    is_fraud, reason, confidence = combine([], None)
    assert (is_fraud, reason, confidence) == (False, "", 0.0)


def test_rule_only_is_fraud_with_confidence_one():
    is_fraud, reason, confidence = combine(["rule:amount_threshold"], None)
    assert is_fraud is True
    assert reason == "rule:amount_threshold"
    assert confidence == 1.0


def test_ml_above_threshold_is_fraud_with_reason_ml():
    is_fraud, reason, confidence = combine([], 0.9)
    assert is_fraud is True
    assert reason == "ml"
    assert confidence == 0.9


def test_ml_below_threshold_alone_is_not_fraud():
    is_fraud, reason, confidence = combine([], 0.5)
    assert is_fraud is False
    assert reason == ""


def test_rule_and_ml_both_trigger_combines_reasons():
    is_fraud, reason, confidence = combine(["rule:velocity"], 0.9)
    assert is_fraud is True
    assert reason == "rule:velocity,ml"
    assert confidence == 0.9
