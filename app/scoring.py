from app.models import ScoreBreakdown, ScreeningConfig, StockSnapshot


def _ratio(value: float, target: float, inverse: bool = False) -> float:
    if target == 0:
        return 1.0
    raw = target / max(value, .0001) if inverse else value / target
    return max(0.0, min(1.0, raw))


def score(snapshot: StockSnapshot, config: ScreeningConfig) -> ScoreBreakdown:
    reasons: list[str] = []
    trend = snapshot.price > snapshot.ema20 > snapshot.ema50 > snapshot.ema200
    rsi_ok = config.rsi_min <= snapshot.rsi <= config.rsi_max
    atr_ok = config.atr_pct_min <= snapshot.atr_pct <= config.atr_pct_max
    technical = 100 * sum([
        0.35 if trend else 0,
        0.20 if rsi_ok else 0,
        0.20 * _ratio(snapshot.adx, config.adx_min),
        0.15 * _ratio(snapshot.rvol, config.rvol_min),
        0.10 if atr_ok else 0,
    ])
    fundamental = 100 * sum([
        .30 * _ratio(snapshot.revenue_growth, config.revenue_growth_min),
        .30 * _ratio(snapshot.eps_growth, config.eps_growth_min),
        .25 * _ratio(snapshot.roic, config.roic_min),
        .15 * _ratio(snapshot.debt_to_equity, config.debt_to_equity_max, inverse=True),
    ])
    institutional = 100 * _ratio(snapshot.institutional_accumulators, config.accumulating_institutions_min)
    insider = 100 * _ratio(snapshot.insider_open_market_purchase_usd, config.insider_purchase_min)
    if trend: reasons.append("Daily EMA trend aligned (price > 20 > 50 > 200)")
    if rsi_ok: reasons.append("RSI is inside the configured range")
    if snapshot.adx >= config.adx_min: reasons.append("ADX confirms trend strength")
    if snapshot.rvol >= config.rvol_min: reasons.append("Relative volume passes threshold")
    if snapshot.institutional_accumulators >= config.accumulating_institutions_min: reasons.append("Institutional accumulation passes threshold")
    if snapshot.insider_open_market_purchase_usd >= config.insider_purchase_min: reasons.append("Material open-market insider purchase")
    total = technical * config.technical_weight + fundamental * config.fundamental_weight + institutional * config.institutional_weight + insider * config.insider_weight
    eligible = trend and rsi_ok and atr_ok and snapshot.adx >= config.adx_min and snapshot.rvol >= config.rvol_min
    return ScoreBreakdown(technical=round(technical, 1), fundamental=round(fundamental, 1), institutional=round(institutional, 1), insider=round(insider, 1), total=round(total, 1), eligible=eligible, reasons=reasons)


