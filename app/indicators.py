from __future__ import annotations


def ema(values: list[float], period: int) -> float:
    if len(values) < period:
        raise ValueError(f"need at least {period} observations")
    value = sum(values[:period]) / period
    multiplier = 2 / (period + 1)
    for item in values[period:]:
        value = (item - value) * multiplier + value
    return value


def rsi(values: list[float], period: int = 14) -> float:
    if len(values) <= period:
        raise ValueError("not enough observations for RSI")
    changes = [values[i] - values[i - 1] for i in range(1, len(values))]
    gains = [max(change, 0) for change in changes]
    losses = [max(-change, 0) for change in changes]
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    for gain, loss in zip(gains[period:], losses[period:]):
        avg_gain = (avg_gain * (period - 1) + gain) / period
        avg_loss = (avg_loss * (period - 1) + loss) / period
    if avg_loss == 0:
        return 100.0
    return 100 - (100 / (1 + avg_gain / avg_loss))


def atr_and_adx(bars: list[dict], period: int = 14) -> tuple[float, float]:
    if len(bars) <= period * 2:
        raise ValueError("not enough observations for ATR/ADX")
    tr, plus_dm, minus_dm = [], [], []
    for previous, current in zip(bars, bars[1:]):
        tr.append(max(current["h"] - current["l"], abs(current["h"] - previous["c"]), abs(current["l"] - previous["c"])))
        up = current["h"] - previous["h"]
        down = previous["l"] - current["l"]
        plus_dm.append(up if up > down and up > 0 else 0)
        minus_dm.append(down if down > up and down > 0 else 0)
    smoothed_tr = sum(tr[:period])
    smoothed_plus = sum(plus_dm[:period])
    smoothed_minus = sum(minus_dm[:period])
    dx = []
    for index in range(period, len(tr)):
        smoothed_tr = smoothed_tr - smoothed_tr / period + tr[index]
        smoothed_plus = smoothed_plus - smoothed_plus / period + plus_dm[index]
        smoothed_minus = smoothed_minus - smoothed_minus / period + minus_dm[index]
        plus_di = 100 * smoothed_plus / smoothed_tr if smoothed_tr else 0
        minus_di = 100 * smoothed_minus / smoothed_tr if smoothed_tr else 0
        total = plus_di + minus_di
        dx.append(100 * abs(plus_di - minus_di) / total if total else 0)
    adx = sum(dx[:period]) / period
    for item in dx[period:]:
        adx = (adx * (period - 1) + item) / period
    return smoothed_tr / period, adx
