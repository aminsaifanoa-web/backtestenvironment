from btfi.data.cache import Cache
from btfi.data.yahoo import YahooFinanceProvider
from btfi.backtesting.engine import BacktestEngine
from btfi.strategies.base import StrategyConfig
from btfi.analytics.metrics import period_metrics, rolling_analysis
from btfi.analytics.verdict import compute_verdict
from btfi.analytics.robustness import parameter_robustness, cost_robustness
import pandas as pd

# Use 30 large-cap proxy to keep downloads feasible and comparable
UNIVERSE_30 = ["AAPL","MSFT","NVDA","AMZN","META","GOOGL","AVGO","LLY","JPM","UNH","V","MA","PG","HD","COST","XOM","JNJ","ABBV","CRM","BAC","WMT","CVX","KO","NFLX","ORCL","MRK","PEP","TMO","ACN","CSCO"]

cache = Cache()
provider = YahooFinanceProvider(cache=cache)
engine = BacktestEngine(provider)

START = "2016-08-27"
END = "2026-08-27"
BENCH = "SPY"

def run_cfg(name, metric, top_n=20, weighting="equal", rebalance="annual", extra=None, universe=None):
    cfg = StrategyConfig(
        name=name,
        universe=",".join(universe or UNIVERSE_30),
        custom_tickers=universe or UNIVERSE_30,
        metric=metric,
        top_n=top_n,
        weighting=weighting,
        rebalance=rebalance,
        transaction_cost_bps=10,
        slippage_bps=5,
        start_date=START,
        end_date=END,
        benchmark=BENCH,
        extra_params=extra or {}
    )
    out = engine.run(cfg)
    eq = out["equity"]
    be = out["benchmark_equity"]
    m = period_metrics(eq, be)
    rolling5 = rolling_analysis(eq, be, 5)
    # quick robustness light
    pr = []
    cr = []
    try:
        pr = parameter_robustness(engine, cfg, "top_n", [10,20,50]) if "pe" in metric.lower() or metric=="pe" else []
    except Exception as e:
        pr = [{"error": str(e)}]
    verdict, reason, score = compute_verdict(m, rolling5, pr, cr, out["warnings"])
    return {"cfg": cfg, "metrics": m, "rolling5": rolling5, "verdict": verdict, "score": score, "warnings": out["warnings"], "equity": eq, "bench": be}

# Checks first
print("=== HEALTH CHECKS ===")
print("Cache size MB:", cache.cache_size_mb())
meta = cache.metadata()
print("Meta rows:", len(meta))
# quick SPY check
import yfinance as yf
df = yf.download("SPY", start=START, end=END, progress=False, auto_adjust=False)
if not df.empty:
    close = df[("Close","SPY")] if isinstance(df.columns, pd.MultiIndex) else df["Close"]
    adj = df[("Adj Close","SPY")] if isinstance(df.columns, pd.MultiIndex) else df["Adj Close"]
    print(f"SPY price {float(close.iloc[0]):.2f}->{float(close.iloc[-1]):.2f} total {float(adj.iloc[0]):.2f}->{float(adj.iloc[-1]):.2f}")
    print(f"SPY total return {(float(adj.iloc[-1])/float(adj.iloc[0])-1)*100:.2f}% CAGR {((float(adj.iloc[-1])/float(adj.iloc[0]))**(1/10)-1)*100:.2f}%")
else:
    print("SPY empty")
print("Universe fetch:", len(provider.get_universe("sp500")), "fallback size", len(UNIVERSE_30))

strategies = [
    ("1. S&P 500 Buy & Hold", "market_cap", 1, "equal", "annual", {}, ["SPY"]),  # special case single SPY
    ("2. Equal-weight S&P 500", "market_cap", 30, "equal", "quarterly", {}, None),
    ("3. Low P/E (Top 20)", "pe", 20, "equal", "annual", {}, None),
    ("4. Low P/B (Top 20)", "pb", 20, "equal", "annual", {}, None),
    ("5. High Dividend Yield (Top 20)", "dividend_yield", 20, "equal", "annual", {}, None),
    ("6. Dividend Growth (Top 20)", "dividend_growth", 20, "equal", "annual", {}, None),
    ("7. High Earnings Yield (Top 20)", "earnings_yield", 20, "equal", "annual", {}, None),
    ("8. High FCF Yield (Top 20)", "fcf_yield", 20, "equal", "annual", {}, None),
    ("9. Low EV/EBITDA (Top 20)", "ev_ebitda", 20, "equal", "annual", {}, None),
    ("10. Low EV/EBIT (Top 20)", "ev_ebit", 20, "equal", "annual", {}, None),
]

results = []
for name, metric, top_n, weighting, rebalance, extra, uni in strategies:
    print(f"\n--- Running {name} ---")
    try:
        # For strategy 1, use custom SPY single holding but need to handle via direct price not engine ranking
        if name.startswith("1."):
            # direct SPY buy-hold via yfinance math, not engine (engine single-ticker bug workaround)
            import yfinance as yf
            df = yf.download("SPY", start=START, end=END, progress=False, auto_adjust=False)
            close = df[("Close","SPY")] if isinstance(df.columns, pd.MultiIndex) else df["Close"]
            adj = df[("Adj Close","SPY")] if isinstance(df.columns, pd.MultiIndex) else df["Adj Close"]
            total_ret = float(adj.iloc[-1])/float(adj.iloc[0]) - 1
            cagr = (float(adj.iloc[-1])/float(adj.iloc[0]))**(1/10) - 1
            # also show price-only
            price_ret = float(close.iloc[-1])/float(close.iloc[0]) -1
            print(f"SPY Buy&Hold total {total_ret*100:.2f}% price {price_ret*100:.2f}% CAGR {cagr*100:.2f}%")
            results.append({"name": name, "cagr": cagr, "total": total_ret, "excess": 0, "verdict": "BASELINE", "note": "SPY proxy"})
            continue
        res = run_cfg(name, metric, top_n, weighting, rebalance, extra, uni)
        m = res["metrics"]
        print(f"CAGR {m['cagr']*100:.2f}% vs S&P {m['benchmark_cagr']*100:.2f}% excess {m['excess_cagr']*100:.2f}% Sharpe {m['sharpe']:.2f} DD {m['max_drawdown']*100:.1f}% Verdict {res['verdict']}")
        if res["rolling5"] and "beat_pct" in res["rolling5"]:
            print(f"5Y win {res['rolling5']['beat_pct']}% median excess {res['rolling5']['median_excess']*100:.2f}%")
        results.append({"name": name, "cagr": m["cagr"], "bench": m["benchmark_cagr"], "excess": m["excess_cagr"], "sharpe": m["sharpe"], "dd": m["max_drawdown"], "verdict": res["verdict"], "score": res["score"]["btfi_score"]})
    except Exception as e:
        import traceback
        traceback.print_exc()
        results.append({"name": name, "error": str(e)})

# summary table
print("\n\n=== SUMMARY TABLE (10Y 2016-2026, 30-stock proxy, 10bps+5bps costs) ===")
for r in results:
    if "error" in r:
        print(f"{r['name']:35} ERROR {r['error'][:80]}")
    elif "total" in r:
        print(f"{r['name']:35} CAGR {r['cagr']*100:5.2f}% Total {r['total']*100:6.2f}% (baseline)")
    else:
        print(f"{r['name']:35} CAGR {r['cagr']*100:5.2f}% vs {r['bench']*100:5.2f}% excess {r['excess']*100:+6.2f}% Sharpe {r['sharpe']:4.2f} DD {r['dd']*100:5.1f}% {r['verdict']} Score {r['score']}")

# also test Low P/E robustness top 10/20/50 detail
print("\n--- Low P/E robustness Top 10/20/50 ---")
try:
    for top in [10,20,50]:
        res = run_cfg(f"Low P/E Top {top}", "pe", top, "equal", "annual", {}, UNIVERSE_30)
        m=res["metrics"]
        print(f"Top {top:2d}: CAGR {m['cagr']*100:5.2f}% excess {m['excess_cagr']*100:+6.2f}%")
except Exception as e:
    print(e)
