from __future__ import annotations
import pandas as pd
import numpy as np
from btfi.strategies.base import Strategy, StrategyConfig
from btfi.strategies.formula import safe_eval_formula

class PriceMomentumStrategy(Strategy):
    """Generic momentum on price series. Computed from Close prices."""
    def __init__(self, config: StrategyConfig, lookback_days: int = 252, skip_last_days: int = 0):
        super().__init__(config)
        self.lookback = lookback_days
        self.skip = skip_last_days

    def compute_signals(self, prices: pd.DataFrame, info_map=None) -> pd.DataFrame:
        # prices: wide DataFrame with tickers columns and Close values? Could be MultiIndex or single
        # Normalize to wide close panel
        close = _extract_close(prices)
        # momentum = price[t] / price[t-lookback] -1, higher is better. For ranking we invert? We'll rank descending as higher better, but base rank asc so we negate
        # We'll return -momentum so lower rank = higher momentum
        mom = close / close.shift(self.lookback) - 1
        if self.skip > 0:
            # 12-1 momentum: skip last 21 days
            # use alternative: mom without last skip => close[t-skip]/close[t-lookback-skip]
            mom = close.shift(self.skip) / close.shift(self.lookback + self.skip) - 1
        # negate for ranking (lower = better)
        signals = -mom
        return signals

class ValueStrategy(Strategy):
    """Value ranking using fundamentals from info_map. Lower metric = cheaper = better for P/E, P/B etc. For yield metrics higher is better so we negate."""
    def compute_signals(self, prices: pd.DataFrame, info_map=None) -> pd.DataFrame:
        close = _extract_close(prices)
        dates = close.index
        tickers = close.columns.tolist()
        metric = self.config.metric
        # Build panel of metric values per ticker (cross-section)
        # If price-based metric (momentum, volatility, market_cap), compute from prices/info
        # For fundamental metrics, use latest info as proxy for all dates (with look-ahead warning)
        # For simplicity produce same signal across all dates (rebalance will use cross-section at that date)
        # Price-based: compute time-varying
        if metric.startswith("momentum"):
            lookback_map = {"momentum_3m": 63, "momentum_6m": 126, "momentum_12m": 252, "momentum_12_1": 252}
            lb = lookback_map.get(metric, 252)
            skip = 21 if metric == "momentum_12_1" else 0
            s = PriceMomentumStrategy(self.config, lb, skip).compute_signals(prices, info_map)
            return s
        elif metric == "volatility":
            # 60d trailing volatility, lower is better? For lowest volatility strategy lower vol is better
            rets = close.pct_change()
            vol = rets.rolling(60).std() * np.sqrt(252)
            # lower vol is better => signal = vol (lower rank wins)
            return vol
        elif metric == "market_cap" and info_map:
            caps = {t: info_map.get(t, {}).get("marketCap", np.nan) for t in tickers}
            # higher cap is "larger" - for buy largest, higher is better => negate
            # We default to ranking where lower signal = selected. So for market_cap we need to know intent: config may say largest vs smallest
            # Use extra_params direction
            direction = self.config.extra_params.get("direction", "largest")  # largest or smallest
            # Create DataFrame repeating caps across dates
            sig = pd.DataFrame(index=dates, columns=tickers, dtype=float)
            for t, c in caps.items():
                val = -c if direction == "largest" else c  # if largest, lower signal => larger cap
                sig[t] = val
            return sig
        elif info_map:
            # fundamental - check if mapped key exists for any ticker
            key_map_check = {
                    "pe": "trailingPE",
                    "pb": "priceToBook",
                    "dividend_yield": "dividendYield",
                    "dividend_growth": "earningsGrowth",
                    "roe": "returnOnEquity",
                    "roic": "returnOnAssets",
                    "market_cap": "marketCap",
                    "fcf_yield": "freeCashflow",
                    "earnings_yield": "trailingPE",
                    "revenue_growth": "revenueGrowth",
                    "earnings_growth": "earningsGrowth",
                    "ev_ebitda": "enterpriseToEbitda",
                    "ev_ebit": "enterpriseToEbitda",
                }
            mapped_key = key_map_check.get(metric)
            has_fund = any(mapped_key in info_map.get(t, {}) and info_map.get(t, {}).get(mapped_key) not in (None, 0) for t in tickers[:5] if mapped_key) if mapped_key else False
            # if no fundamental data at all, fall through to random proxy
            if not has_fund and metric not in ("market_cap", "volatility") and not metric.startswith("momentum"):
                # try still to build signals from available data, else fallback
                pass
            sig = pd.DataFrame(index=dates, columns=tickers, dtype=float)
            for t in tickers:
                info = info_map.get(t, {})
                # map metric to yfinance info keys
                key_map = {
                    "pe": "trailingPE",
                    "pb": "priceToBook",
                    "dividend_yield": "dividendYield",
                    "dividend_growth": "earningsGrowth",  # proxy: yfinance lacks dividendGrowth; use earningsGrowth as closest
                    "roe": "returnOnEquity",
                    "roic": "returnOnAssets",  # proxy
                    "market_cap": "marketCap",
                    "fcf_yield": "freeCashflow",
                    "earnings_yield": "trailingEps",
                    "revenue_growth": "revenueGrowth",
                    "earnings_growth": "earningsGrowth",
                    "ev_ebitda": "enterpriseToEbitda",
                    "ev_ebit": "enterpriseToEbitda",
                }
                raw = info.get(key_map.get(metric, metric), np.nan)
                if metric in ("dividend_yield","dividend_growth","fcf_yield","earnings_yield","roe","roic","revenue_growth","earnings_growth"):
                    sig[t] = - (raw if raw is not None else np.nan)
                else:
                    sig[t] = raw if raw is not None else np.nan
                if metric == "fcf_yield":
                    fcf = info.get("freeCashflow", np.nan)
                    mc = info.get("marketCap", np.nan)
                    y = (fcf / mc) if fcf and mc else np.nan
                    sig[t] = -y if y==y else np.nan
                if metric == "earnings_yield":
                    pe = info.get("trailingPE", np.nan)
                    y = 1/pe if pe and pe != 0 else np.nan
                    sig[t] = -y if y==y else np.nan
                if metric == "dividend_growth":
                    # try 3yr dividend proxy via earningsGrowth; already set but refine
                    g = info.get("earningsGrowth", info.get("revenueGrowth", np.nan))
                    sig[t] = -g if g==g and g is not None else np.nan
                if metric in ("ev_ebitda","ev_ebit"):
                    # lower EV multiple = cheaper => keep raw (lower is better)
                    v = info.get("enterpriseToEbitda", np.nan) if metric=="ev_ebitda" else info.get("enterpriseToRevenue", np.nan)
                    # enterpriseToEbitda already lower=cheaper, keep as is; if missing use enterpriseValue/trailingEbit?
                    if pd.isna(v):
                        ev = info.get("enterpriseValue", np.nan)
                        ebitda = info.get("ebitda", np.nan)
                        if ev and ebitda:
                            v = ev/ebitda
                    sig[t] = v if v==v else np.nan
            return sig
        else:
            # fallback random or price-based
            # alphabetical or random handled via extra_params
            if self.config.extra_params.get("weird") == "alphabetical":
                sig = pd.DataFrame(index=dates, columns=tickers, dtype=float)
                sorted_t = sorted(tickers)
                rank_map = {t: i for i, t in enumerate(sorted_t)}
                for t in tickers:
                    sig[t] = rank_map[t]
                return sig
            if self.config.extra_params.get("weird") == "random":
                rng = np.random.default_rng(42)
                sig = pd.DataFrame(rng.random((len(dates), len(tickers))), index=dates, columns=tickers)
                return sig
            # default: use trailing return as proxy for value? just return price rank
            rng = np.random.default_rng(0)
            sig = pd.DataFrame(rng.random((len(dates), len(tickers))), index=dates, columns=tickers)
            return sig

class MultifactorStrategy(Strategy):
    def compute_signals(self, prices: pd.DataFrame, info_map=None) -> pd.DataFrame:
        # Use formula field
        formula = self.config.formula or "rank(momentum_12m)"
        # Need to build metric panel at each date
        # For simplicity, evaluate formula cross-sectionally at each date using metric proxies
        close = _extract_close(prices)
        dates = close.index
        tickers = close.columns.tolist()
        # Build per-date metric DataFrame and evaluate
        signals = pd.DataFrame(index=dates, columns=tickers, dtype=float)
        # Precompute metric series per ticker for price-based metrics across time
        price_metrics = {}
        # momentum and volatility time series
        rets = close.pct_change()
        vol_series = rets.rolling(60).std() * np.sqrt(252)
        mom3 = close / close.shift(63) - 1
        mom6 = close / close.shift(126) - 1
        mom12 = close / close.shift(252) - 1
        mom12_1 = close.shift(21) / close.shift(273) - 1
        for dt in dates:
            row = {}
            # collect metric values for this date across tickers
            # Build df where rows=tickers, cols=metrics
            metrics_at_dt = {}
            for t in tickers:
                info = (info_map or {}).get(t, {})
                # compute values
                vals = {}
                vals["momentum_3m"] = mom3.loc[dt, t] if dt in mom3.index else np.nan
                vals["momentum_6m"] = mom6.loc[dt, t] if dt in mom6.index else np.nan
                vals["momentum_12m"] = mom12.loc[dt, t] if dt in mom12.index else np.nan
                vals["momentum_12_1"] = mom12_1.loc[dt, t] if dt in mom12_1.index else np.nan
                vals["volatility"] = vol_series.loc[dt, t] if dt in vol_series.index else np.nan
                vals["market_cap"] = info.get("marketCap", np.nan)
                vals["pe"] = info.get("trailingPE", np.nan)
                vals["pb"] = info.get("priceToBook", np.nan)
                vals["dividend_yield"] = info.get("dividendYield", np.nan)
                vals["dividend_growth"] = info.get("earningsGrowth", info.get("revenueGrowth", np.nan))
                vals["roe"] = info.get("returnOnEquity", np.nan)
                vals["roic"] = info.get("returnOnAssets", np.nan)
                fcf = info.get("freeCashflow", np.nan)
                mc = info.get("marketCap", np.nan)
                vals["fcf_yield"] = (fcf/mc) if fcf and mc and mc!=0 else np.nan
                pe = info.get("trailingPE", np.nan)
                vals["earnings_yield"] = (1/pe) if pe and pe!=0 else np.nan
                vals["revenue_growth"] = info.get("revenueGrowth", np.nan)
                vals["earnings_growth"] = info.get("earningsGrowth", np.nan)
                vals["ev_ebitda"] = info.get("enterpriseToEbitda", np.nan)
                vals["ev_ebit"] = info.get("enterpriseToRevenue", np.nan)
                metrics_at_dt[t] = vals
            df = pd.DataFrame.from_dict(metrics_at_dt, orient="index")
            try:
                # evaluate formula: expects rank etc operating on columns vectors
                result = safe_eval_formula(formula, df)
                # result should be Series indexed by ticker
                if isinstance(result, pd.Series):
                    for t in tickers:
                        if t in result.index:
                            signals.loc[dt, t] = result.loc[t]
                elif isinstance(result, (int, float, np.number)):
                    signals.loc[dt, :] = float(result)
                else:
                    # if DataFrame or other, take first column
                    signals.loc[dt, :] = 0
            except Exception:
                signals.loc[dt, :] = np.nan
        # For selection, lower signal = better? Our formula builds score where higher rank => higher weight? We'll ensure ranking ascending picks lower signal
        # If formula yields higher = better, user can negate via rank ordering; we keep as is
        return signals

def _extract_close(prices: pd.DataFrame) -> pd.DataFrame:
    if prices is None or prices.empty:
        return pd.DataFrame()
    if isinstance(prices.columns, pd.MultiIndex):
        # try to get Close
        try:
            if "Close" in prices.columns.get_level_values(1):
                close = prices.xs("Close", axis=1, level=1)
            elif "Adj Close" in prices.columns.get_level_values(1):
                close = prices.xs("Adj Close", axis=1, level=1)
            else:
                close = prices.xs(prices.columns.get_level_values(1)[0], axis=1, level=1)
        except Exception:
            # fallback: first level tickers
            close = pd.DataFrame(index=prices.index)
            for t in prices.columns.get_level_values(0).unique():
                try:
                    sub = prices[t]
                    if "Close" in sub.columns:
                        close[t] = sub["Close"]
                    else:
                        close[t] = sub.iloc[:,0]
                except Exception:
                    continue
        close.index = pd.to_datetime(close.index)
        return close.sort_index()
    else:
        # single ticker or flat
        if "Close" in prices.columns:
            s = prices["Close"]
            # need ticker name? use column name as ticker if unknown
            # If single ticker, create DataFrame with one column
            if isinstance(s, pd.Series):
                name = getattr(prices, "ticker", "TICKER")
                # try to infer from data? fallback to first ticker param
                df = pd.DataFrame({str(name): s})
                df.index = pd.to_datetime(df.index)
                return df
            return pd.DataFrame(s)
        else:
            # assume prices is already close panel (columns=tickers)
            prices.index = pd.to_datetime(prices.index)
            return prices
