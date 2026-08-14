from shared.schema import TransactionEvent
from consumer.rules import RuleEngine
from consumer import reasons


def _event(user_id="u1", amount=10.0, country="US"):
    return TransactionEvent(
        transaction_id="t", user_id=user_id, amount=amount, currency="USD",
        merchant="Amazon", country=country, timestamp="2026-08-14T00:00:00+00:00",
        source="synthetic",
    )


def test_amount_above_threshold_is_flagged():
    engine = RuleEngine()
    triggered = engine.evaluate(_event(amount=6000.0), now_epoch=0)
    assert reasons.AMOUNT_THRESHOLD in triggered


def test_amount_below_threshold_is_not_flagged():
    engine = RuleEngine()
    triggered = engine.evaluate(_event(amount=10.0), now_epoch=0)
    assert reasons.AMOUNT_THRESHOLD not in triggered


def test_sixth_transaction_within_window_is_flagged_for_velocity():
    engine = RuleEngine()
    for i in range(5):
        engine.evaluate(_event(user_id="u1"), now_epoch=float(i))
    triggered = engine.evaluate(_event(user_id="u1"), now_epoch=5.0)
    assert reasons.VELOCITY in triggered


def test_transactions_outside_window_do_not_count_toward_velocity():
    engine = RuleEngine()
    for i in range(5):
        engine.evaluate(_event(user_id="u1"), now_epoch=float(i))
    triggered = engine.evaluate(_event(user_id="u1"), now_epoch=200.0)
    assert reasons.VELOCITY not in triggered


def test_country_change_for_known_user_is_flagged():
    engine = RuleEngine()
    engine.evaluate(_event(user_id="u1", country="US"), now_epoch=0)
    triggered = engine.evaluate(_event(user_id="u1", country="DE"), now_epoch=1)
    assert reasons.GEO_MISMATCH in triggered


def test_first_transaction_for_user_is_never_geo_flagged():
    engine = RuleEngine()
    triggered = engine.evaluate(_event(user_id="new_user", country="DE"), now_epoch=0)
    assert reasons.GEO_MISMATCH not in triggered
