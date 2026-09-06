import json
import os

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.catalyst import MarketConfirmation, NewsItem, assess_catalyst
from app.demo import snapshots
from app.learning import propose
from app.models import Outcome, ScreeningConfig, StockSnapshot
from app.scoring import score
from app.storage import Store
from app.providers.alpaca import AlpacaConfigurationError, AlpacaMarketData
from app.providers.news import FreeNewsProvider

app = FastAPI(title="AI Stock Researcher", version="0.2.0", description="Research-only decision support; no brokerage execution.")
store = Store(os.getenv("DATABASE_PATH", "data/researcher.db"))
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
def home(): return FileResponse("static/index.html")


@app.get("/api/health")
def health(): return {"status": "ok", "mode": "demo", "brokerage_execution": False, "catalyst_engine": True}


@app.get("/api/providers/alpaca/status")
def alpaca_status():
    try:
        provider = AlpacaMarketData()
        symbols = provider.active_us_symbols()
        provider.close()
        return {"configured": True, "authenticated": True, "active_us_symbols": len(symbols), "orders_enabled": False}
    except AlpacaConfigurationError:
        return {"configured": False, "authenticated": False, "active_us_symbols": 0, "orders_enabled": False}
    except httpx.HTTPError as exc:
        return {"configured": True, "authenticated": False, "active_us_symbols": 0, "orders_enabled": False, "error": type(exc).__name__}


@app.get("/api/news/{ticker}")
def news(ticker: str, company_name: str | None = None, limit_per_source: int = 10):
    provider = FreeNewsProvider()
    try:
        return provider.collect(ticker, company_name, min(max(limit_per_source, 1), 25))
    finally:
        provider.close()


@app.post("/api/catalyst/assess")
def catalyst_assess(item: NewsItem, surprise_impact: float = 0.0):
    return assess_catalyst(item, surprise_impact=surprise_impact)


@app.post("/api/catalyst/assess-with-market")
def catalyst_assess_with_market(item: NewsItem, market: MarketConfirmation, surprise_impact: float = 0.0):
    return assess_catalyst(item, market=market, surprise_impact=surprise_impact)


@app.get("/api/config")
def get_config(): return store.get_config()


@app.put("/api/config")
def put_config(config: ScreeningConfig):
    store.save_config(config)
    return config


@app.post("/api/score")
def score_one(snapshot: StockSnapshot): return score(snapshot, store.get_config())


@app.post("/api/scan")
def scan_demo():
    return rank_and_store(snapshots())


def rank_and_store(universe: list[StockSnapshot]):
    config = store.get_config()
    ranked = []
    for snapshot in universe:
        result = score(snapshot, config)
        if result.eligible:
            rid = store.add_recommendation(snapshot, result)
            ranked.append({"id": rid, "ticker": snapshot.ticker, "price": snapshot.price, "score": result})
    return sorted(ranked, key=lambda x: x["score"].total, reverse=True)[:5]


@app.post("/api/scan/snapshots")
def scan_snapshots(universe: list[StockSnapshot]):
    """Score timestamped snapshots supplied by a licensed market-data collector."""
    return rank_and_store(universe)


@app.get("/api/recommendations")
def recommendations():
    return [{**r, "scores": json.loads(r["scores"])} for r in store.recent()]


@app.post("/api/outcomes")
def add_outcome(outcome: Outcome):
    try: store.add_outcome(outcome)
    except ValueError as exc: raise HTTPException(404, str(exc)) from exc
    return {"status": "recorded"}


@app.get("/api/learning/proposal")
def learning_proposal(): return propose(store.outcome_rows())
