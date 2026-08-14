from sklearn.metrics import precision_score, recall_score

MIN_PRECISION = 0.80
MIN_RECALL = 0.70


def validate(model, X_test, y_test) -> dict:
    y_pred = model.predict(X_test)
    return {
        "precision": precision_score(y_test, y_pred),
        "recall": recall_score(y_test, y_pred),
    }


def assert_meets_bar(metrics: dict) -> None:
    assert metrics["precision"] >= MIN_PRECISION, f"precision {metrics['precision']:.3f} below bar {MIN_PRECISION}"
    assert metrics["recall"] >= MIN_RECALL, f"recall {metrics['recall']:.3f} below bar {MIN_RECALL}"
