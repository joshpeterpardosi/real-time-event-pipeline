from generator.synthetic import generate_event, should_inject_fraud, AMOUNT_FRAUD_FLOOR


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


def test_default_ratio_injects_every_twentieth_event():
    injected = [sent for sent in range(40) if should_inject_fraud(sent, fraud_ratio=0.05)]
    assert injected == [0, 20]


def test_zero_ratio_never_injects():
    assert not any(should_inject_fraud(sent, fraud_ratio=0.0) for sent in range(20))


def test_ratio_of_one_injects_every_event():
    assert all(should_inject_fraud(sent, fraud_ratio=1.0) for sent in range(10))
