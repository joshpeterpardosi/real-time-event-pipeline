from generator.replay import row_to_event


def _sample_row():
    row = {f"V{i}": str(i * 0.1) for i in range(1, 29)}
    row.update({"Time": "406", "Amount": "99.99", "Class": "1"})
    return row


def test_row_to_event_source_is_replay():
    event = row_to_event(_sample_row())
    assert event.source == "replay"


def test_row_to_event_maps_v1_to_v28_into_features_in_order():
    event = row_to_event(_sample_row())
    assert event.features == [round(i * 0.1, 4) for i in range(1, 29)]


def test_row_to_event_does_not_leak_class_label():
    event = row_to_event(_sample_row())
    assert not hasattr(event, "label")
    assert "Class" not in event.__dict__
