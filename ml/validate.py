from sklearn.metrics import precision_score, recall_score

from shared.thresholds import ML_FRAUD_THRESHOLD

MIN_PRECISION = 0.80
MIN_RECALL = 0.70


def validate(model, X_test, y_test, threshold: float = ML_FRAUD_THRESHOLD) -> dict:
    """Score the model at the threshold the consumer actually uses.

    `model.predict` applies the implicit 0.5, which is not the point this
    pipeline runs at — the bar below would then be certifying behaviour nobody
    ships. Defaulting to ``ML_FRAUD_THRESHOLD`` keeps the gate honest.
    """
    y_pred = model.predict_proba(X_test)[:, 1] >= threshold
    return {
        "threshold": threshold,
        "precision": precision_score(y_test, y_pred, zero_division=0),
        "recall": recall_score(y_test, y_pred, zero_division=0),
    }


def assert_meets_bar(metrics: dict) -> None:
    assert metrics["precision"] >= MIN_PRECISION, f"precision {metrics['precision']:.3f} below bar {MIN_PRECISION}"
    assert metrics["recall"] >= MIN_RECALL, f"recall {metrics['recall']:.3f} below bar {MIN_RECALL}"
