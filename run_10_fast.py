from btfi.data.cache import Cache
from btfi.data.yahoo import YahooFinanceProvider
from btfi.backtesting.engine import BacktestEngine
from btfi.strategies.base import StrategyConfig
from btfi.analytics.metrics import period_metrics, rolling_analysis
from btfi.analytics.verdict import compute_verdict
import time

UNIVERSE_30 = ["AAPL","MSFT","NVDA","AMZN","META","GOOGL","AVGO","LLY","JPM","UNH","V","MA","PG","HD","COST","XOM","JNJ","ABBV","CRM","BAC","WMT","CVX","KO","NFLX","ORCL","MRK","PEP","TMO","ACN","CSCO"]
cache = Cache()
provider = YahooFinanceProvider(cache=cache)
engine = BacktestEngine(provider)
START = "2016-08-27"
END = "2026-08-27"
BENCH = "SPY"

def run_one(name, metric, top_n=20, extra=None):
    t0=time.time()
    cfg = StrategyConfig(name=name, custom_tickers=UNIVERSE_30, universe=",".join(UNIVERSE_30), metric=metric, top_n=top_n, weighting="equal", rebalance="annual", transaction_cost_bps=10, slippage_bps=5, start_date=START, end_date=END, benchmark=BENCH, extra_params=extra or {})
    out = engine.run(cfg)
    eq, be = out["equity"], out["benchmark_equity"]
    m = period_metrics(eq, be)
    roll5 = rolling_analysis(eq, be, 5)
    verdict, reason, score = compute_verdict(m, roll5, [], [], out["warnings"])
    print(f"{name:35} CAGR {m['cagr']*100:5.2f}% vs {m['benchmark_cagr']*100:5.2f}% excess {m['excess_cagr']*100:+6.2f}% Sharpe {m['sharpe']:4.2f} DD {m['max_drawdown']*100:5.1f}% 5Ywin {roll5.get('beat_pct',0):4.1f}% {verdict} Score {score['btfi_score']:.1f} ({time.time()-t0:.1f}s)")
    return m

print("=== 10 STRATEGIES 2016-2026 30-stock proxy price-only vs SPY ===")
# 1 baseline already known
print("1. S&P 500 Buy & Hold (SPY total) 311.87% total 15.21% CAGR (Adj Close) // engine bench 13.39% price-only")
strategies = [
    ("2. Equal-weight S&P (30)", "market_cap"),
    ("3. Low P/E Top10", "pe"),
    ("3b Low P/E Top20", "pe"),
    ("3c Low P/E Top50", "pe"),
    ("4. Low P/B Top20", "pb"),
    ("5. High Div Yield Top20", "dividend_yield"),
    ("6. Div Growth Top20", "dividend_growth"),
    ("7. High Earnings Yield Top20", "earnings_yield"),
    ("8. High FCF Yield Top20", "fcf_yield"),
    ("9. Low EV/EBITDA Top20", "ev_ebitda"),
    ("10. Low EV/EBIT Top20", "ev_ebit"),
]
# Need handle Top variations
for name, metric in strategies:
    if "Top10" in name:
        run_one(name, metric, top_n=10)
    elif "Top50" in name:
        run_one(name, "pe", top_n=50)
    elif "Equal-weight" in name:
        run_one(name, "market_cap", top_n=30, extra={})
    else:
        # for equal weight we need all 30, but metric market_cap with direction largest? Actually equal weight just picks all tickers equally, not rank. We'll still use market_cap but top_n 30 picks all 30 equally -> equal weight
        run_one(name, metric, top_n=20)
