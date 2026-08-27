"""End-to-end test: provider -> universe -> strategy -> backtest -> metrics -> robustness -> report -> export"""
import pandas as pd
import numpy as np
from unittest.mock import MagicMock
from btfi.strategies.base import StrategyConfig
from btfi.backtesting.engine import BacktestEngine
from btfi.analytics.metrics import period_metrics, rolling_analysis, annual_returns
from btfi.analytics.robustness import parameter_robustness, cost_robustness
from btfi.analytics.verdict import compute_verdict
from btfi.reports.generator import generate_markdown

def make_mock_provider():
    dates = pd.date_range("2018-01-01", "2023-12-31", freq="B")
    np.random.seed(123)
    tickers = ["AAPL","MSFT","NVDA"]
    data = {}
    for t in tickers:
        rets = np.random.randn(len(dates))*0.012
        price = 100*np.exp(np.cumsum(rets))
        data[t] = pd.DataFrame({"Close": price}, index=dates)
    combined = pd.concat(data, axis=1)
    # Make MultiIndex with Close level
    combined.columns = pd.MultiIndex.from_tuples([(t,"Close") for t in tickers])
    provider = MagicMock()
    def get_prices(tickers, start, end, auto_adjust=False):
        # limit dates
        s = pd.to_datetime(start); e = pd.to_datetime(end)
        sub = combined.loc[(combined.index>=s)&(combined.index<=e)]
        if len(tickers)==1 and tickers[0]=="SPY":
            # benchmark synthetic
            bench_dates = pd.date_range(start, end, freq="B")
            np.random.seed(999)
            bench_price = 300*np.exp(np.cumsum(np.random.randn(len(bench_dates))*0.008))
            df = pd.DataFrame({"Close": bench_price}, index=bench_dates)
            df.columns = pd.MultiIndex.from_tuples([("SPY","Close")])
            return df
        return sub
    provider.get_prices.side_effect = get_prices
    provider.get_universe.return_value = tickers
    provider.get_info.return_value = {"marketCap": 5e9, "trailingPE": 18, "dividendYield": 0.02}
    provider.get_dividends.return_value = pd.Series(dtype=float)
    return provider

def test_e2e():
    provider = make_mock_provider()
    eng = BacktestEngine(provider)
    cfg = StrategyConfig(name="Low PE Test", metric="momentum_12m", top_n=1, rebalance="annual", start_date="2018-01-01", end_date="2023-12-31", benchmark="SPY")
    out = eng.run(cfg)
    equity = out["equity"]
    bench = out["benchmark_equity"]
    metrics = period_metrics(equity, bench)
    rolling = rolling_analysis(equity, bench, 1)
    annual = annual_returns(equity, bench)
    pr = parameter_robustness(eng, cfg)
    cr = cost_robustness(eng, cfg)
    verdict, reason, score = compute_verdict(metrics, rolling, pr, cr, out.get("warnings",[]))
    md = generate_markdown(1, "Test", cfg.to_dict(), metrics, annual, verdict, reason, out.get("warnings",[]), rolling, score)
    assert "BTFI #001" in md
    assert verdict in ["BUY THE FUCKING INDEX","ACTUALLY FUCKING WORKS","INTERESTING, BUT NOT ROBUST","FUCKED BY COSTS","DATA TOO SHITTY TO KNOW"]
    assert metrics["cagr"] is not None
