from unittest.mock import MagicMock
from shared.schema import TransactionEvent
from consumer.rules import RuleEngine
from consumer.consumer import process_message
from consumer import reasons


def test_malformed_json_returns_none():
    result = process_message("not-json", RuleEngine(), MagicMock(), now_epoch=0)
    assert result is None


def test_valid_synthetic_high_amount_is_flagged_by_rule():
    event = TransactionEvent(
        transaction_id="t1", user_id="u1", amount=9000.0, currency="USD",
        merchant="Amazon", country="US", timestamp="2026-08-14T00:00:00+00:00",
        source="synthetic",
    )
    mock_ml = MagicMock()
    mock_ml.score.return_value = None

    row = process_message(event.to_json(), RuleEngine(), mock_ml, now_epoch=0)

    assert row["transaction_id"] == "t1"
    assert row["is_fraud"] == 1
    assert reasons.AMOUNT_THRESHOLD in row["fraud_reason"]


def test_valid_replay_event_flagged_by_ml_score():
    event = TransactionEvent(
        transaction_id="t2", user_id="kaggle_1", amount=10.0, currency="USD",
        merchant="unknown", country="US", timestamp="2026-08-14T00:00:00+00:00",
        source="replay", features=[0.0] * 28,
    )
    mock_ml = MagicMock()
    mock_ml.score.return_value = 0.95

    row = process_message(event.to_json(), RuleEngine(), mock_ml, now_epoch=0)

    assert row["is_fraud"] == 1
    assert row["fraud_reason"] == reasons.ML
    assert row["confidence_score"] == 0.95
