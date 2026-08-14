from generator.synthetic import generate_event, AMOUNT_FRAUD_FLOOR


def test_generate_event_source_is_synthetic_with_no_features():
    event = generate_event()
    assert event.source == "synthetic"
    assert event.features is None


def test_generate_event_normal_amount_below_fraud_floor():
    event = generate_event(inject_fraud=False)
    assert event.amount < AMOUNT_FRAUD_FLOOR


def test_generate_event_inject_fraud_amount_at_or_above_floor():
    event = generate_event(inject_fraud=True)
    assert event.amount >= AMOUNT_FRAUD_FLOOR
