from __future__ import annotations

from datetime import date, timedelta

from app.indicators import atr_and_adx, ema, rsi
from app.models import ScreeningConfig
from app.providers.alpaca import AlpacaMarketData


# A bounded, liquid research universe keeps scans reliable on the free service.
DEFAULT_UNIVERSE = [
    "AAPL", "ABBV", "AMD", "AMZN", "AVGO", "BAC", "BRK.B", "COST", "CRM", "CSCO",
    "CVX", "DIS", "GOOGL", "HD", "INTC", "JNJ", "JPM", "KO", "LLY", "MA",
    "META", "MRK", "MSFT", "NFLX", "NVDA", "ORCL", "PEP", "PFE", "PG", "QCOM",
    "TMO", "TSLA", "UNH", "V", "WMT", "XOM",
]


def scan_live(config: ScreeningConfig) -> list[dict]:
    provider = AlpacaMarketData()
    try:
        end = date.today() + timedelta(days=1)
        bars_by_symbol = provider.daily_bars(DEFAULT_UNIVERSE, end - timedelta(days=420), end)
    finally:
        provider.close()

    candidates = []
    for symbol, bars in bars_by_symbol.items():
        if len(bars) < 201:
            continue
        closes = [float(bar["c"]) for bar in bars]
        volumes = [float(bar["v"]) for bar in bars]
        price = closes[-1]
        e20, e50, e200 = ema(closes, 20), ema(closes, 50), ema(closes, 200)
        rsi14 = rsi(closes)
        atr14, adx14 = atr_and_adx(bars)
        average_volume = sum(volumes[-30:]) / min(30, len(volumes))
        previous_average = sum(volumes[-31:-1]) / min(30, len(volumes) - 1)
        rvol = volumes[-1] / previous_average if previous_average else 0
        atr_pct = 100 * atr14 / price
        roc9 = 100 * (price / closes[-10] - 1)
        checks = {
            "ema_trend": price > e20 > e50 > e200,
            "rsi": config.rsi_min <= rsi14 <= config.rsi_max,
            "adx": adx14 > config.adx_min,
            "rvol": rvol >= config.rvol_min,
            "atr": config.atr_pct_min <= atr_pct <= config.atr_pct_max,
            "volume": average_volume > config.average_volume_30d_min,
            "roc": roc9 > config.roc_9_min,
        }
        if all(checks.values()):
            strength = sum([35, 20, min(20, 20 * adx14 / max(config.adx_min, 1)), 15, 10])
            candidates.append({
                "ticker": symbol, "price": round(price, 2), "score": round(strength, 1),
                "ema20": round(e20, 2), "ema50": round(e50, 2), "ema200": round(e200, 2),
                "rsi": round(rsi14, 1), "adx": round(adx14, 1), "rvol": round(rvol, 2),
                "atr_pct": round(atr_pct, 2), "average_volume_30d": round(average_volume),
                "roc_9": round(roc9, 2), "data_as_of": bars[-1].get("t"),
                "scope": "live_technical_only",
                "reasons": ["Live Alpaca daily data", "Price > EMA20 > EMA50 > EMA200", "RSI, ADX, volume and ROC pass"],
            })
    return sorted(candidates, key=lambda item: item["score"], reverse=True)[:10]
