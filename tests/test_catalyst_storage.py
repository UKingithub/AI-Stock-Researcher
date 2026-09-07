from app.catalyst import CatalystEvent, CatalystOutcome, NewsItem, assess_catalyst
from app.storage import Store


def event() -> CatalystEvent:
    return CatalystEvent(
        ticker="abc",
        event_price=100,
        item=NewsItem(source="SEC", source_type="sec", title="Company raised guidance", url="https://example.test"),
        market_regime="uptrend",
    )


def test_catalyst_event_and_forward_returns_are_persisted(tmp_path):
    store = Store(str(tmp_path / "test.db"))
    catalyst_event = event()
    event_id = store.add_catalyst_event(catalyst_event, assess_catalyst(catalyst_event.item))
    result = store.add_catalyst_outcome(CatalystOutcome(event_id=event_id, horizon_days=5, exit_price=108))

    assert result == 8
    evidence = store.catalyst_evidence()
    assert evidence[0]["ticker"] == "ABC"
    assert evidence[0]["horizon_days"] == 5
    assert evidence[0]["market_regime"] == "uptrend"


def test_missing_catalyst_event_is_rejected(tmp_path):
    store = Store(str(tmp_path / "test.db"))
    try:
        store.add_catalyst_outcome(CatalystOutcome(event_id=999, horizon_days=1, exit_price=10))
    except ValueError as exc:
        assert str(exc) == "catalyst event not found"
    else:
        raise AssertionError("missing catalyst event should fail")
