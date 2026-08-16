import numpy as np

from consumer.combine import combine
from consumer import reasons
from ml.validate import validate
from shared.thresholds import ML_FRAUD_THRESHOLD


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


def test_serving_and_validation_agree_on_the_threshold():
    """The consumer's flag boundary and the gate in ml/validate.py must be the
    same number. If they drift, the precision/recall bar certifies an operating
    point the pipeline never runs."""
    just_below = ML_FRAUD_THRESHOLD - 0.01
    just_at = ML_FRAUD_THRESHOLD

    assert combine([], just_below)[0] is False
    assert combine([], just_at)[0] is True

    class _AtThreshold:
        def predict_proba(self, X):
            return np.array([[1 - just_at, just_at]])

    assert validate(_AtThreshold(), X_test=[[0]], y_test=[1])["recall"] == 1.0
