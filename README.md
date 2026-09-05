# AI Stock Researcher

A research-only MVP for ranking 3–10 day US equity swing candidates with user-configurable technical, fundamental, institutional and insider criteria.

## Safety boundary

- No brokerage integration or automatic execution.
- Scores are deterministic and preserve the underlying evidence.
- Insider points refer to open-market purchases, not grants or option exercises.
- Adaptive learning requires at least 30 completed outcomes and only proposes changes for human approval.
- Demo data is synthetic/sample data and is visibly labelled. This is decision support, not financial advice.

## Included

- Mobile-friendly installable web dashboard (PWA)
- Configurable RSI, ADX, RVOL, ATR, growth, ROIC, leverage, institutional and insider thresholds
- Configurable category weights, validated to total 100%
- Recommendation snapshots and 5/10-day outcome storage
- MFE/MAE fields and controlled weight proposals
- FastAPI endpoints, SQLite persistence, Docker packaging and CI tests

## Run locally

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
uvicorn app.main:app --reload
```

Open `http://localhost:8000`. The MVP defaults to demo mode; no API key is needed.

## API overview

- `GET /api/config` and `PUT /api/config`
- `POST /api/score` for externally collected snapshots
- `POST /api/scan` for the demo universe
- `GET /api/recommendations`
- `POST /api/outcomes` for 5/10-day observations
- `GET /api/learning/proposal`

## Next data-integration milestone

Add provider adapters behind `StockSnapshot`: SEC EDGAR (filings/Form 4/13D/13G), a licensed market/fundamentals feed, calendar-aware event risk, and price-history-derived multi-timeframe indicators. Provider failures and data timestamps should remain explicit; missing evidence must never be silently scored as bullish.


