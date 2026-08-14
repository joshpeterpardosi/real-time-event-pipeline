import json
from shared.schema import TransactionEvent


def test_to_json_round_trips_all_fields():
    event = TransactionEvent(
        transaction_id="t1", user_id="u1", amount=12.5, currency="USD",
        merchant="Amazon", country="US", timestamp="2026-08-14T00:00:00+00:00",
        source="synthetic",
    )
    restored = TransactionEvent.from_json(event.to_json())
    assert restored == event


def test_to_json_includes_features_when_present():
    event = TransactionEvent(
        transaction_id="t1", user_id="u1", amount=12.5, currency="USD",
        merchant="unknown", country="US", timestamp="2026-08-14T00:00:00+00:00",
        source="replay", features=[0.1, 0.2],
    )
    data = json.loads(event.to_json())
    assert data["features"] == [0.1, 0.2]


def test_default_features_is_none():
    event = TransactionEvent(
        transaction_id="t1", user_id="u1", amount=12.5, currency="USD",
        merchant="Amazon", country="US", timestamp="2026-08-14T00:00:00+00:00",
        source="synthetic",
    )
    assert event.features is None
