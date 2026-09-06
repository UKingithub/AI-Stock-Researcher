from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel, Field

CatalystDirection = Literal["strong_bearish", "bearish", "neutral", "bullish", "strong_bullish"]


class NewsItem(BaseModel):
    source: str
    title: str
    url: str
    published_at: str | None = None
    summary: str = ""
    source_type: Literal["sec", "company", "wire", "news", "aggregator"] = "news"


class MarketConfirmation(BaseModel):
    price_change_pct: float | None = None
    relative_volume: float | None = None
    above_vwap: bool | None = None
    broke_resistance: bool | None = None


class CatalystAssessment(BaseModel):
    score: int = Field(ge=-100, le=100)
    direction: CatalystDirection
    category: str
    source_credibility: float = Field(ge=0, le=1)
    fundamental_impact: float = Field(ge=-1, le=1)
    surprise_impact: float = Field(ge=-1, le=1)
    market_confirmation: float = Field(ge=-1, le=1)
    reasons: list[str]
    caution: str | None = None


SOURCE_CREDIBILITY = {
    "sec": 1.00,
    "company": 0.90,
    "wire": 0.85,
    "news": 0.70,
    "aggregator": 0.55,
}

# Rules are intentionally transparent and conservative. They are a baseline,
# not a substitute for an LLM or event-specific financial analysis.
BULLISH_RULES: list[tuple[str, float, str]] = [
    (r"\braise[sd]? guidance\b|\bguidance (?:raised|increased)\b", 0.90, "raised_guidance"),
    (r"\bbeats? (?:estimates|expectations|consensus)\b|\bearnings beat\b", 0.75, "earnings_beat"),
    (r"\b(repurchase|buyback)\b", 0.45, "buyback"),
    (r"\b(open.market|insider) (?:buy|purchase)\b|\binsider buying\b", 0.55, "insider_buying"),
    (r"\b(fda|regulatory) approval\b|\bapproved by the fda\b", 0.95, "regulatory_approval"),
    (r"\bawarded?\b.*\bcontract\b|\bwins?\b.*\bcontract\b", 0.70, "major_contract"),
    (r"\bdebt (?:reduction|repaid|paydown)\b", 0.45, "deleveraging"),
]

BEARISH_RULES: list[tuple[str, float, str]] = [
    (r"\bcut[s]? guidance\b|\bguidance (?:cut|lowered|reduced)\b", -0.90, "guidance_cut"),
    (r"\bmiss(?:es|ed)? (?:estimates|expectations|consensus)\b|\bearnings miss\b", -0.75, "earnings_miss"),
    (r"\b(dilution|dilutive|share offering|secondary offering|at.the.market offering)\b", -0.85, "dilution"),
    (r"\b(fda|regulatory) (?:rejection|rejects|rejected|denial)\b", -0.95, "regulatory_rejection"),
    (r"\b(default|bankruptcy|going concern|liquidity crisis)\b", -1.00, "financial_distress"),
    (r"\b(restatement|accounting irregularit|fraud investigation)\b", -0.90, "accounting_risk"),
    (r"\bceo resigns?\b|\bcfo resigns?\b", -0.45, "executive_departure"),
]


def _rule_signal(text: str) -> tuple[float, str, list[str]]:
    hits: list[tuple[float, str]] = []
    lowered = text.lower()
    for pattern, weight, category in [*BULLISH_RULES, *BEARISH_RULES]:
        if re.search(pattern, lowered):
            hits.append((weight, category))
    if not hits:
        return 0.0, "unclear", ["No high-confidence deterministic catalyst rule matched"]
    hits.sort(key=lambda x: abs(x[0]), reverse=True)
    strongest = hits[0]
    combined = max(-1.0, min(1.0, sum(weight for weight, _ in hits)))
    reasons = [f"Matched catalyst rule: {category}" for _, category in hits]
    return combined, strongest[1], reasons


def _confirmation_signal(market: MarketConfirmation | None) -> tuple[float, list[str]]:
    if market is None:
        return 0.0, ["No market-confirmation data supplied"]
    points = 0.0
    reasons: list[str] = []
    if market.price_change_pct is not None:
        points += max(-0.4, min(0.4, market.price_change_pct / 20.0))
        reasons.append(f"Price reaction: {market.price_change_pct:+.2f}%")
    if market.relative_volume is not None:
        if market.relative_volume >= 2:
            points += 0.2 if (market.price_change_pct or 0) >= 0 else -0.2
            reasons.append(f"High relative volume: {market.relative_volume:.2f}x")
    if market.above_vwap is True:
        points += 0.2
        reasons.append("Price is above VWAP")
    elif market.above_vwap is False:
        points -= 0.2
        reasons.append("Price is below VWAP")
    if market.broke_resistance is True:
        points += 0.2
        reasons.append("Price broke resistance")
    return max(-1.0, min(1.0, points)), reasons


def _direction(score: int) -> CatalystDirection:
    if score >= 70:
        return "strong_bullish"
    if score >= 30:
        return "bullish"
    if score <= -70:
        return "strong_bearish"
    if score <= -30:
        return "bearish"
    return "neutral"


def assess_catalyst(
    item: NewsItem,
    market: MarketConfirmation | None = None,
    surprise_impact: float = 0.0,
) -> CatalystAssessment:
    """Score a catalyst from -100 to +100 using transparent baseline rules.

    surprise_impact is an optional normalized value [-1, 1] supplied by a
    separate expectations/consensus model. The market component deliberately
    cannot overpower the underlying event by itself.
    """
    credibility = SOURCE_CREDIBILITY[item.source_type]
    fundamental, category, rule_reasons = _rule_signal(f"{item.title}. {item.summary}")
    confirmation, market_reasons = _confirmation_signal(market)
    surprise = max(-1.0, min(1.0, surprise_impact))

    raw = 100 * (
        0.55 * fundamental * credibility
        + 0.20 * surprise
        + 0.25 * confirmation
    )
    score = int(round(max(-100, min(100, raw))))
    caution = None
    if fundamental > 0 and confirmation < -0.2:
        caution = "Positive headline but negative market reaction; avoid treating this as a confirmed long catalyst."
    elif fundamental < 0 and confirmation > 0.2:
        caution = "Negative headline but positive market reaction; the event may be priced in or less material than expected."

    return CatalystAssessment(
        score=score,
        direction=_direction(score),
        category=category,
        source_credibility=credibility,
        fundamental_impact=round(fundamental, 3),
        surprise_impact=round(surprise, 3),
        market_confirmation=round(confirmation, 3),
        reasons=[*rule_reasons, *market_reasons],
        caution=caution,
    )
