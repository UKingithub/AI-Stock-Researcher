from app.catalyst import MarketConfirmation, NewsItem, assess_catalyst


def item(title: str, source_type: str = "sec") -> NewsItem:
    return NewsItem(source="test", title=title, url="https://example.test/item", source_type=source_type)


def test_raised_guidance_is_bullish():
    result = assess_catalyst(item("Company raised guidance after earnings"))
    assert result.score > 0
    assert result.category == "raised_guidance"


def test_dilution_is_bearish():
    result = assess_catalyst(item("Company announces share offering and dilution"))
    assert result.score < 0
    assert result.category == "dilution"


def test_positive_news_negative_reaction_gets_caution():
    market = MarketConfirmation(price_change_pct=-8, relative_volume=3, above_vwap=False)
    result = assess_catalyst(item("Company raised guidance"), market)
    assert result.caution is not None
    assert "negative market reaction" in result.caution


def test_source_credibility_changes_magnitude():
    primary = assess_catalyst(item("Company raised guidance", "sec"))
    aggregator = assess_catalyst(item("Company raised guidance", "aggregator"))
    assert primary.score > aggregator.score
