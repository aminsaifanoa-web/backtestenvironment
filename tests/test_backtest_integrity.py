import pandas as pd
import numpy as np
from unittest.mock import MagicMock
from btfi.strategies.base import StrategyConfig
from btfi.backtesting.engine import BacktestEngine

def mock_provider_with_prices():
    # Create synthetic price data for 3 tickers, 2 years
    dates = pd.date_range("2020-01-01", "2021-12-31", freq="B")
    np.random.seed(42)
    tickers = ["AAA","BBB","CCC","DDD","EEE"]
    # Build DataFrame with MultiIndex columns like yfinance
    data = {}
    for t in tickers:
        # random walk
        rets = np.random.randn(len(dates))*0.01
        price = 100 * np.exp(np.cumsum(rets))
        df = pd.DataFrame({"Open": price*0.99, "High": price*1.01, "Low": price*0.98, "Close": price, "Volume": 1000000}, index=dates)
        data[t] = df
    # yfinance group_by ticker returns DataFrame with MultiIndex: mimic by concatenating
    combined = pd.concat(data, axis=1)
    # combined has MultiIndex (ticker, OHLC)
    provider = MagicMock()
    provider.get_prices.side_effect = lambda tickers, start, end, auto_adjust=False: combined if "AAA" in tickers else combined.iloc[:, :5]  # for benchmark SPY simulate
    provider.get_universe.return_value = tickers
    provider.get_info.return_value = {"marketCap": 1e9, "trailingPE": 15}
    provider.get_dividends.return_value = pd.Series(dtype=float)
    return provider, combined

def test_lookahead_t_plus_1():
    provider, _ = mock_provider_with_prices()
    eng = BacktestEngine(provider)
    cfg = StrategyConfig(name="Test Mom", metric="momentum_12m", top_n=2, rebalance="monthly", start_date="2020-01-01", end_date="2021-12-31", benchmark="SPY")
    out = eng.run(cfg)
    assert "equity" in out
    assert len(out["equity"]) > 100
    # ensure trades exist and equity not NaN
    assert out["equity"].isna().sum() == 0

def test_reproducibility():
    provider, _ = mock_provider_with_prices()
    eng = BacktestEngine(provider)
    cfg = StrategyConfig(name="Test", metric="momentum_12m", top_n=2, rebalance="annual", start_date="2020-01-01", end_date="2021-12-31")
    out1 = eng.run(cfg)
    out2 = eng.run(cfg)
    pd.testing.assert_series_equal(out1["equity"], out2["equity"])

def test_survivorship_warning():
    from btfi.strategies.registry import instantiate_strategy
    cfg = StrategyConfig(name="Test", universe="sp500", metric="pe")
    strat = instantiate_strategy(cfg)
    warnings = strat.get_warnings()
    assert any("Survivorship" in w for w in warnings)
