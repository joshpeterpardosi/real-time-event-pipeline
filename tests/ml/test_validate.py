import numpy as np
import pytest
from ml.validate import validate, assert_meets_bar
from shared.thresholds import ML_FRAUD_THRESHOLD


class _StubModel:
    """Returns fixed positive-class probabilities, so the threshold under test is
    the only thing that decides the labels."""

    def __init__(self, probabilities):
        self._probabilities = probabilities

    def predict_proba(self, X):
        p = np.asarray(self._probabilities, dtype=float)
        return np.column_stack([1.0 - p, p])


def test_validate_computes_precision_and_recall_against_hand_worked_example():
    # At the 0.7 threshold these probabilities flag idx 0 and 3:
    # TP=2 (idx 0,3), FP=0, FN=1 (idx 2) -> precision=2/2=1.0, recall=2/3≈0.667
    model = _StubModel([0.95, 0.10, 0.20, 0.80, 0.05])
    y_test = [1, 0, 1, 1, 0]
    metrics = validate(model, X_test=[[0]] * 5, y_test=y_test)
    assert metrics["precision"] == pytest.approx(1.0)
    assert metrics["recall"] == pytest.approx(2 / 3)


def test_validate_scores_at_the_threshold_the_consumer_uses():
    """The gate must certify the operating point that ships. A score of 0.6 is
    fraud under the implicit 0.5 that `model.predict` would apply, and not fraud
    at the consumer's 0.7 — so the two must not disagree."""
    model = _StubModel([0.6, 0.6])
    metrics = validate(model, X_test=[[0]] * 2, y_test=[1, 1])

    assert metrics["threshold"] == ML_FRAUD_THRESHOLD
    # Nothing clears 0.7, so recall is 0 — which is the honest reading of what
    # the pipeline would do with this model, not what predict() implies.
    assert metrics["recall"] == pytest.approx(0.0)


def test_validate_accepts_an_explicit_threshold():
    model = _StubModel([0.6, 0.6])
    metrics = validate(model, X_test=[[0]] * 2, y_test=[1, 1], threshold=0.5)
    assert metrics["threshold"] == 0.5
    assert metrics["recall"] == pytest.approx(1.0)


def test_assert_meets_bar_raises_when_precision_below_bar():
    with pytest.raises(AssertionError):
        assert_meets_bar({"precision": 0.5, "recall": 0.9})


def test_assert_meets_bar_passes_when_both_above_bar():
    assert_meets_bar({"precision": 0.95, "recall": 0.9})  # no raise
