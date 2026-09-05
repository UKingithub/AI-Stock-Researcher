import httpx

from app.providers.alpaca import AlpacaMarketData


def test_client_is_read_only_and_filters_us_assets():
    def handler(request):
        assert request.headers["APCA-API-KEY-ID"] == "key"
        return httpx.Response(200, json=[
            {"symbol": "AAPL", "tradable": True, "exchange": "NASDAQ"},
            {"symbol": "OTC1", "tradable": True, "exchange": "OTC"},
            {"symbol": "HALT", "tradable": False, "exchange": "NYSE"},
        ])
    provider = AlpacaMarketData("key", "secret", transport=httpx.MockTransport(handler))
    assert provider.active_us_symbols() == ["AAPL"]
    assert not hasattr(provider, "submit_order")
    provider.close()


