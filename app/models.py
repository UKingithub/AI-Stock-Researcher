from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field, model_validator


class ScreeningConfig(BaseModel):
    rsi_min: float = Field(50, ge=0, le=100)
    rsi_max: float = Field(65, ge=0, le=100)
    adx_min: float = Field(20, ge=0)
    rvol_min: float = Field(1.5, ge=0)
    atr_pct_min: float = Field(2, ge=0)
    atr_pct_max: float = Field(4.5, ge=0)
    revenue_growth_min: float = 15
    eps_growth_min: float = 15
    roic_min: float = 10
    debt_to_equity_max: float = Field(1.5, ge=0)
    insider_purchase_min: float = Field(100_000, ge=0)
    accumulating_institutions_min: int = Field(3, ge=0)
    technical_weight: float = Field(.30, ge=0)
    fundamental_weight: float = Field(.30, ge=0)
    institutional_weight: float = Field(.20, ge=0)
    insider_weight: float = Field(.20, ge=0)

    @model_validator(mode="after")
    def validate_ranges(self):
        if self.rsi_min > self.rsi_max or self.atr_pct_min > self.atr_pct_max:
            raise ValueError("minimum values must not exceed maximum values")
        total = self.technical_weight + self.fundamental_weight + self.institutional_weight + self.insider_weight
        if abs(total - 1) > .001:
            raise ValueError("weights must total 1.0")
        return self


class StockSnapshot(BaseModel):
    ticker: str
    price: float = Field(gt=0)
    ema20: float
    ema50: float
    ema200: float
    rsi: float
    adx: float
    rvol: float
    atr_pct: float
    revenue_growth: float
    eps_growth: float
    roic: float
    debt_to_equity: float
    institutional_accumulators: int = 0
    insider_open_market_purchase_usd: float = 0
    insider_role: str | None = None
    data_as_of: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ScoreBreakdown(BaseModel):
    technical: float
    fundamental: float
    institutional: float
    insider: float
    total: float
    eligible: bool
    reasons: list[str]


class Recommendation(BaseModel):
    ticker: str
    entry_price: float
    score: ScoreBreakdown
    created_at: datetime


class Outcome(BaseModel):
    recommendation_id: int
    horizon_days: Literal[5, 10]
    exit_price: float = Field(gt=0)
    mfe_pct: float | None = None
    mae_pct: float | None = None


class LearningProposal(BaseModel):
    status: Literal["insufficient_data", "review_required"]
    sample_size: int
    message: str
    proposed_weights: dict[str, float] | None = None


