from __future__ import annotations
import pandas as pd
import numpy as np

TRADING_DAYS = 252

def cagr(equity: pd.Series) -> float:
    if equity.empty or equity.iloc[0] == 0:
        return 0.0
    total = equity.iloc[-1] / equity.iloc[0]
    years = (equity.index[-1] - equity.index[0]).days / 365.25
    if years <= 0:
        return 0.0
    return float(total ** (1/years) - 1)

def total_return(equity: pd.Series) -> float:
    if equity.empty or equity.iloc[0]==0:
        return 0.0
    return float(equity.iloc[-1]/equity.iloc[0] -1)

def annualized_vol(returns: pd.Series) -> float:
    if returns.empty:
        return 0.0
    return float(returns.std(ddof=0) * np.sqrt(TRADING_DAYS))

def sharpe(returns: pd.Series, rf: float = 0.0) -> float:
    vol = annualized_vol(returns)
    if vol == 0:
        return 0.0
    ann_ret = returns.mean() * TRADING_DAYS
    return float((ann_ret - rf) / vol)

def sortino(returns: pd.Series, rf: float = 0.0) -> float:
    downside = returns[returns < 0]
    if downside.empty:
        return float(sharpe(returns, rf))
    dd = downside.std(ddof=0) * np.sqrt(TRADING_DAYS)
    if dd == 0:
        return 0.0
    ann_ret = returns.mean() * TRADING_DAYS
    return float((ann_ret - rf) / dd)

def max_drawdown(equity: pd.Series) -> tuple[float, float, int]:
    """return (max_dd, avg_dd, longest_dd_days)"""
    cummax = equity.cummax()
    dd = (equity - cummax) / cummax
    max_dd = float(dd.min())
    avg_dd = float(dd[dd<0].mean()) if (dd<0).any() else 0.0
    # longest drawdown period
    is_dd = dd < 0
    longest = 0
    cur = 0
    max_cur = 0
    for v in is_dd:
        if v:
            cur += 1
            max_cur = max(max_cur, cur)
        else:
            cur = 0
    longest = max_cur
    return max_dd, avg_dd, longest

def calmar(cagr_val: float, max_dd: float) -> float:
    if max_dd == 0:
        return 0.0
    return float(cagr_val / abs(max_dd))

def beta_alpha(strategy_rets: pd.Series, bench_rets: pd.Series) -> tuple[float,float]:
    if len(strategy_rets) < 10:
        return 0.0, 0.0
    cov = np.cov(strategy_rets, bench_rets, ddof=0)[0,1]
    var_b = np.var(bench_rets)
    beta = cov/var_b if var_b != 0 else 0.0
    # alpha annualized
    alpha = strategy_rets.mean()*TRADING_DAYS - beta*bench_rets.mean()*TRADING_DAYS
    return float(beta), float(alpha)

def tracking_error(strategy_rets: pd.Series, bench_rets: pd.Series) -> float:
    excess = strategy_rets - bench_rets
    return float(excess.std(ddof=0)*np.sqrt(TRADING_DAYS))

def information_ratio(strategy_rets: pd.Series, bench_rets: pd.Series) -> float:
    excess = strategy_rets - bench_rets
    te = excess.std(ddof=0)*np.sqrt(TRADING_DAYS)
    if te == 0:
        return 0.0
    return float((excess.mean()*TRADING_DAYS)/te)

def annual_returns(equity: pd.Series, benchmark_equity: pd.Series) -> pd.DataFrame:
    strat_rets = equity.resample("YE").last().pct_change()
    bench_rets = benchmark_equity.resample("YE").last().pct_change()
    # align years
    years = sorted(set(strat_rets.index.year.dropna().astype(int).tolist()) | set(bench_rets.index.year.dropna().astype(int).tolist()))
    rows = []
    for y in years:
        # find last equity of that year
        try:
            s_val = strat_rets[strat_rets.index.year==y]
            b_val = bench_rets[bench_rets.index.year==y]
            s = float(s_val.iloc[0]) if not s_val.empty and pd.notna(s_val.iloc[0]) else np.nan
            b = float(b_val.iloc[0]) if not b_val.empty and pd.notna(b_val.iloc[0]) else np.nan
            excess = s - b if pd.notna(s) and pd.notna(b) else np.nan
            rows.append({"year": int(y), "strategy": s, "benchmark": b, "excess": excess})
        except Exception:
            continue
    df = pd.DataFrame(rows)
    return df

def period_metrics(equity: pd.Series, bench_eq: pd.Series) -> dict:
    strat_rets = equity.pct_change().fillna(0)
    bench_rets = bench_eq.pct_change().fillna(0)
    c = cagr(equity)
    bc = cagr(bench_eq)
    vol = annualized_vol(strat_rets)
    bvol = annualized_vol(bench_rets)
    sh = sharpe(strat_rets)
    so = sortino(strat_rets)
    mdd, avg_dd, longest = max_drawdown(equity)
    bmdd, _, _ = max_drawdown(bench_eq)
    beta, alpha = beta_alpha(strat_rets, bench_rets)
    te = tracking_error(strat_rets, bench_rets)
    ir = information_ratio(strat_rets, bench_rets)
    tr = total_return(equity)
    btr = total_return(bench_eq)
    return {
        "cagr": c,
        "benchmark_cagr": bc,
        "excess_cagr": c - bc,
        "total_return": tr,
        "benchmark_total_return": btr,
        "volatility": vol,
        "benchmark_volatility": bvol,
        "sharpe": sh,
        "sortino": so,
        "max_drawdown": mdd,
        "benchmark_max_drawdown": bmdd,
        "avg_drawdown": avg_dd,
        "calmar": calmar(c, mdd),
        "beta": beta,
        "alpha": alpha,
        "tracking_error": te,
        "information_ratio": ir,
        "correlation": float(strat_rets.corr(bench_rets)) if len(strat_rets)>2 else 0.0,
    }

def rolling_analysis(equity: pd.Series, bench_eq: pd.Series, window_years: int = 1) -> dict:
    days = window_years * 252
    if len(equity) < days + 5:
        return {"window_years": window_years, "error": "Insufficient historical data.", "win_rate": None, "periods": []}
    rolls = []
    wins = 0
    total = 0
    for i in range(len(equity) - days):
        start = equity.index[i]
        end = equity.index[i+days]
        s_eq = equity.loc[start:end]
        b_eq = bench_eq.loc[start:end]
        if s_eq.empty or b_eq.empty:
            continue
        s_cagr = cagr(s_eq)
        b_cagr = cagr(b_eq)
        excess = s_cagr - b_cagr
        rolls.append({"start": str(start.date()), "end": str(end.date()), "strategy_cagr": s_cagr, "benchmark_cagr": b_cagr, "excess": excess})
        if excess > 0:
            wins += 1
        total += 1
    win_rate = wins/total if total else 0
    return {
        "window_years": window_years,
        "periods": rolls[:1000],  # cap
        "total_periods": total,
        "win_rate": win_rate,
        "beat_pct": round(win_rate*100,1),
        "lose_pct": round((1-win_rate)*100,1),
        "median_excess": float(np.median([r["excess"] for r in rolls])) if rolls else 0,
    }

def start_date_robustness(equity: pd.Series, bench_eq: pd.Series, window_years: int = 5) -> dict:
    days = window_years * 252
    if len(equity) < days + 10:
        return {"window_years": window_years, "error": "Insufficient historical data."}
    cagrs = []
    excesses = []
    beats = 0
    total = 0
    for i in range(len(equity)-days):
        s_eq = equity.iloc[i:i+days+1]
        b_eq = bench_eq.iloc[i:i+days+1]
        s_cagr = cagr(s_eq)
        b_cagr = cagr(b_eq)
        cagrs.append(s_cagr)
        excesses.append(s_cagr - b_cagr)
        if s_cagr > b_cagr:
            beats += 1
        total += 1
    return {
        "window_years": window_years,
        "median_cagr": float(np.median(cagrs)) if cagrs else 0,
        "mean_cagr": float(np.mean(cagrs)) if cagrs else 0,
        "best_cagr": float(np.max(cagrs)) if cagrs else 0,
        "worst_cagr": float(np.min(cagrs)) if cagrs else 0,
        "median_excess": float(np.median(excesses)) if excesses else 0,
        "mean_excess": float(np.mean(excesses)) if excesses else 0,
        "win_rate": beats/total if total else 0,
        "beat_pct": round(beats/total*100,1) if total else 0,
    }

def required_periods(equity: pd.Series, bench_eq: pd.Series) -> dict:
    out = {}
    for yrs in [1,2,5,10,20]:
        days = yrs*252
        if len(equity) >= days + 2:
            s_eq = equity.iloc[-days-1:]
            b_eq = bench_eq.iloc[-days-1:]
            out[f"{yrs}Y"] = {"strategy_cagr": cagr(s_eq), "benchmark_cagr": cagr(b_eq), "excess": cagr(s_eq)-cagr(b_eq)}
        else:
            out[f"{yrs}Y"] = {"error": "Insufficient historical data."}
    return out
