from app.models import StockSnapshot


def snapshots():
    return [
        StockSnapshot(ticker="NVDA",price=182,ema20=178,ema50=165,ema200=140,rsi=58,adx=29,rvol=1.9,atr_pct=3.2,average_volume_30d=45_000_000,roc_9=4.2,net_margin=55,revenue_growth=32,eps_growth=38,roic=24,debt_to_equity=.42,institutional_accumulators=8,insider_open_market_purchase_usd=0),
        StockSnapshot(ticker="MSFT",price=524,ema20=518,ema50=505,ema200=470,rsi=55,adx=24,rvol=1.6,atr_pct=2.2,average_volume_30d=22_000_000,roc_9=2.1,net_margin=36,revenue_growth=18,eps_growth=20,roic=27,debt_to_equity=.35,institutional_accumulators=6,insider_open_market_purchase_usd=0),
        StockSnapshot(ticker="DEMO",price=64,ema20=61,ema50=57,ema200=49,rsi=56,adx=31,rvol=2.3,atr_pct=3.8,average_volume_30d=1_200_000,roc_9=5.4,net_margin=14,revenue_growth=28,eps_growth=35,roic=18,debt_to_equity=.3,institutional_accumulators=9,insider_open_market_purchase_usd=350000,insider_role="CEO"),
    ]

