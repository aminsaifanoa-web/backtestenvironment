import pandas as pd
import numpy as np
from btfi.analytics.metrics import cagr, sharpe, max_drawdown, beta_alpha, annualized_vol, period_metrics

def test_cagr():
    idx = pd.date_range("2020-01-01", periods=252*2, freq="B")
    eq = pd.Series(np.linspace(10000, 15000, len(idx)), index=idx)
    c = cagr(eq)
    assert 0.15 < c < 0.30

def test_max_drawdown():
    idx = pd.date_range("2020-01-01", periods=10, freq="D")
    eq = pd.Series([100,120,80,90,100,70,110,100,90,100], index=idx)
    mdd, avg, longest = max_drawdown(eq)
    assert mdd < 0
    assert mdd <= -0.3

def test_sharpe_zero_vol():
    rets = pd.Series([0.01]*100)
    # vol may be 0 -> sharpe 0
    s = sharpe(rets)
    assert s == 0 or np.isfinite(s)

def test_beta_alpha():
    strat = pd.Series(np.random.randn(100)*0.01)
    bench = pd.Series(np.random.randn(100)*0.01)
    beta, alpha = beta_alpha(strat, bench)
    assert isinstance(beta, float)

def test_period_metrics_basic():
    idx = pd.date_range("2020-01-01", periods=252, freq="B")
    eq = pd.Series(10000*(1+np.random.randn(len(idx))*0.01).cumprod(), index=idx)
    # ensure positive
    eq = eq - eq.min() + 9000
    bench = pd.Series(10000*(1+np.random.randn(len(idx))*0.008).cumprod(), index=idx)
    bench = bench - bench.min() + 9000
    m = period_metrics(eq, bench)
    assert "cagr" in m and "sharpe" in m
