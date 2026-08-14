import pytest
from ml.validate import validate, assert_meets_bar


class _StubModel:
    def predict(self, X):
        return [1, 0, 0, 1, 0]


def test_validate_computes_precision_and_recall_against_hand_worked_example():
    # y_test / predict() chosen so precision/recall are hand-computable:
    # TP=2 (idx 0,3), FP=0, FN=1 (idx 2) -> precision=2/2=1.0, recall=2/3≈0.667
    y_test = [1, 0, 1, 1, 0]
    metrics = validate(_StubModel(), X_test=[[0]] * 5, y_test=y_test)
    assert metrics["precision"] == pytest.approx(1.0)
    assert metrics["recall"] == pytest.approx(2 / 3)


def test_assert_meets_bar_raises_when_precision_below_bar():
    with pytest.raises(AssertionError):
        assert_meets_bar({"precision": 0.5, "recall": 0.9})


def test_assert_meets_bar_passes_when_both_above_bar():
    assert_meets_bar({"precision": 0.95, "recall": 0.9})  # no raise
