from __future__ import annotations

import os
from datetime import date

import httpx


class AlpacaConfigurationError(RuntimeError):
    pass


class AlpacaMarketData:
    """Read-only Alpaca client. This class intentionally exposes no order methods."""

    data_url = "https://data.alpaca.markets"
    paper_url = "https://paper-api.alpaca.markets"

    def __init__(self, key_id: str | None = None, secret_key: str | None = None, transport=None):
        self.key_id = key_id or os.getenv("APCA_API_KEY_ID")
        self.secret_key = secret_key or os.getenv("APCA_API_SECRET_KEY")
        if not self.key_id or not self.secret_key:
            raise AlpacaConfigurationError("Alpaca credentials are not configured")
        self.client = httpx.Client(
            headers={"APCA-API-KEY-ID": self.key_id, "APCA-API-SECRET-KEY": self.secret_key},
            timeout=30,
            transport=transport,
        )

    def active_us_symbols(self) -> list[str]:
        response = self.client.get(
            f"{self.paper_url}/v2/assets",
            params={"status": "active", "asset_class": "us_equity"},
        )
        response.raise_for_status()
        return sorted(
            asset["symbol"] for asset in response.json()
            if asset.get("tradable") and asset.get("exchange") in {"NASDAQ", "NYSE", "AMEX", "ARCA", "BATS", "NYSEARCA"}
        )

    def daily_bars(self, symbols: list[str], start: date, end: date, feed: str = "sip") -> dict[str, list[dict]]:
        """Fetch adjusted daily OHLCV bars, following Alpaca pagination."""
        bars: dict[str, list[dict]] = {symbol: [] for symbol in symbols}
        page_token = None
        while True:
            params = {
                "symbols": ",".join(symbols), "timeframe": "1Day",
                "start": start.isoformat(), "end": end.isoformat(),
                "adjustment": "all", "feed": feed, "limit": 10_000,
            }
            if page_token:
                params["page_token"] = page_token
            response = self.client.get(f"{self.data_url}/v2/stocks/bars", params=params)
            response.raise_for_status()
            payload = response.json()
            for symbol, items in payload.get("bars", {}).items():
                bars.setdefault(symbol, []).extend(items)
            page_token = payload.get("next_page_token")
            if not page_token:
                return bars

    def close(self):
        self.client.close()


