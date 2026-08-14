from unittest.mock import MagicMock, patch
import pytest
from shared.schema import TransactionEvent


def _event(features=None):
    return TransactionEvent(
        transaction_id="t", user_id="u1", amount=10.0, currency="USD",
        merchant="unknown", country="US", timestamp="2026-08-14T00:00:00+00:00",
        source="replay" if features else "synthetic", features=features,
    )


@patch("consumer.ml_scorer.joblib.load")
def test_score_returns_none_when_features_absent(mock_load):
    from consumer.ml_scorer import MLScorer
    mock_load.return_value = MagicMock()
    scorer = MLScorer(model_path="model.joblib")

    assert scorer.score(_event(features=None)) is None


@patch("consumer.ml_scorer.joblib.load")
def test_score_returns_positive_class_probability_when_features_present(mock_load):
    from consumer.ml_scorer import MLScorer
    mock_model = MagicMock()
    mock_model.predict_proba.return_value = [[0.1, 0.9]]
    mock_load.return_value = mock_model
    scorer = MLScorer(model_path="model.joblib")

    score = scorer.score(_event(features=[0.0] * 28))

    assert score == 0.9


@patch("consumer.ml_scorer.joblib.load", side_effect=OSError("file not found"))
def test_load_failure_raises_runtime_error(mock_load):
    from consumer.ml_scorer import MLScorer
    with pytest.raises(RuntimeError):
        MLScorer(model_path="missing.joblib")
