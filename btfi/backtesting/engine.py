from __future__ import annotations
import pandas as pd
import numpy as np
from dataclasses import asdict
from btfi.strategies.base import StrategyConfig
from btfi.strategies.registry import instantiate_strategy
from btfi.portfolio.accounting import Portfolio
# We need _extract_close locally to avoid circular import; define helper
def _extract_close_local(prices: pd.DataFrame) -> pd.DataFrame:
    if prices is None or prices.empty:
        return pd.DataFrame()
    if isinstance(prices.columns, pd.MultiIndex):
        try:
            if "Close" in prices.columns.get_level_values(1):
                close = prices.xs("Close", axis=1, level=1)
            else:
                close = prices.xs(prices.columns.get_level_values(1)[0], axis=1, level=1)
        except Exception:
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
        if "Close" in prices.columns:
            s = prices["Close"]
            df = pd.DataFrame({"SPY": s}) if isinstance(s, pd.Series) and prices.shape[1] <= 6 else pd.DataFrame(s)
            df.index = pd.to_datetime(df.index)
            return df.sort_index()
        prices.index = pd.to_datetime(prices.index)
        return prices.sort_index()

class BacktestEngine:
    """Event/time-series backtester. Look-ahead bias: signal at t executes at t+1 close."""

    def __init__(self, provider):
        self.provider = provider

    def run(self, config: StrategyConfig, benchmark_prices: pd.DataFrame | None = None) -> dict:
        # 1. Determine universe
        tickers = self._get_universe(config)
        if not tickers:
            raise ValueError("Empty universe")

        # 2. Fetch prices
        prices_raw = self.provider.get_prices(tickers, config.start_date, config.end_date, auto_adjust=False)
        close = _extract_close_local(prices_raw)
        if close.empty:
            raise ValueError("No price data retrieved")

        # 3. Fetch benchmark
        bench_close = None
        bench_rets = None
        if config.benchmark:
            try:
                bench_raw = self.provider.get_prices([config.benchmark], config.start_date, config.end_date, auto_adjust=False)
                bench_close_df = _extract_close_local(bench_raw)
                # bench_close_df has one column
                bench_close = bench_close_df.iloc[:,0] if not bench_close_df.empty else None
                if bench_close is not None:
                    bench_rets = bench_close.pct_change().fillna(0)
            except Exception:
                bench_close = None

        # 4. Fetch info_map for fundamentals (with survivorship warning, we use current info as proxy)
        info_map = {}
        for t in tickers[:100]:  # limit to avoid rate limits; top N likely within first 100
            try:
                info_map[t] = self.provider.get_info(t) or {}
            except Exception:
                info_map[t] = {}
        # Also ensure all tickers have entry
        for t in tickers:
            if t not in info_map:
                info_map[t] = {}

        # 5. Strategy signals
        strat = instantiate_strategy(config)
        signals = strat.compute_signals(prices_raw, info_map)  # DataFrame index dates, columns tickers, values signal

        # Align signals index to close index
        signals = signals.reindex(close.index)

        # 6. Determine rebalance dates: use strategy's rebalance schedule but also ensure first date is available
        all_dates = close.index
        rebalance_dates = strat.rebalance_dates(all_dates)
        # Ensure we have at least first and last
        if len(rebalance_dates) == 0:
            rebalance_dates = all_dates[::252]  # annual fallback

        # 7. Portfolio simulation with t+1 execution
        port = Portfolio(initial_capital=10000.0, transaction_cost_bps=config.transaction_cost_bps, slippage_bps=config.slippage_bps)
        # Track equity curve
        equity = pd.Series(index=close.index, dtype=float)
        holdings_history = []

        # Precompute price dicts per date for speed
        # Dividends handling: fetch dividends for each ticker and inject as cash on ex-date
        div_map = {}
        for t in tickers:
            try:
                divs = self.provider.get_dividends(t)
                if divs is not None and not divs.empty:
                    divs.index = pd.to_datetime(divs.index)
                    div_map[t] = divs
            except Exception:
                continue

        # Iterate chronologically
        rebalance_set = set(rebalance_dates)
        # For look-ahead: signal at t executes at t+1, so we store pending target
        pending_target: dict | None = None
        pending_date: pd.Timestamp | None = None

        for i, dt in enumerate(close.index):
            # Apply dividends to cash before valuation
            for t, divs in div_map.items():
                if dt in divs.index:
                    shares = port.holdings.get(t, 0)
                    if shares > 0:
                        port.cash += shares * float(divs.loc[dt])

            # Execute pending rebalance from prior signal date
            if pending_target is not None and pending_date is not None:
                # prices at execution date dt
                px = {t: float(close.loc[dt, t]) for t in pending_target if t in close.columns and pd.notna(close.loc[dt, t])}
                # filter to available prices
                avail = {t: w for t, w in pending_target.items() if t in px}
                if avail:
                    # normalize weights if some tickers missing price
                    tot = sum(avail.values())
                    if tot > 0:
                        avail = {t: w/tot for t, w in avail.items()}
                    port.rebalance_to_target(avail, px, dt)
                pending_target = None
                pending_date = None

            # Current valuation
            cur_prices = {}
            for t in close.columns:
                v = close.loc[dt, t]
                if pd.notna(v):
                    cur_prices[t] = float(v)
            eq = port.value(cur_prices)
            equity.loc[dt] = eq

            # Check if this date is a rebalance signal date
            if dt in rebalance_set:
                # Need signals at this date
                if dt in signals.index:
                    row = signals.loc[dt]
                    if row.notna().sum() >= 2:
                        ranked = row.rank(ascending=True)
                        selected = strat.select(ranked, config)
                        if selected:
                            # compute target weights
                            weights = strat.weight(selected, signals=row, prices=prices_raw, info_map=info_map)
                            # Schedule execution at t+1 (next trading day)
                            pending_target = weights
                            pending_date = dt
                holdings_history.append({"date": dt, "holdings": list(port.holdings.keys()), "cash": port.cash, "value": eq})

        # Fill NaN equity forward
        equity = equity.ffill().fillna(10000)

        # Build returns
        strat_rets = equity.pct_change().fillna(0)
        # Align benchmark to same index
        if bench_close is not None:
            # Reindex benchmark close to strategy dates, forward fill
            bc = bench_close.reindex(close.index).ffill()
            bench_eq = bc / bc.iloc[0] * 10000
            bench_rets_aligned = bench_eq.pct_change().fillna(0)
        else:
            bench_eq = pd.Series(10000, index=close.index)
            bench_rets_aligned = pd.Series(0, index=close.index)

        # Handle corporate actions: splits already adjusted via Close? yfinance Close is adjusted for splits; we use Close not Adj Close? For portfolio accounting we use Close which is split-adjusted via yfinance download auto_adjust=False gives raw Close plus we rely on yfinance adjustments? We disclose limitation
        return {
            "equity": equity,
            "benchmark_equity": bench_eq if bench_close is not None else equity*0+10000,
            "strategy_returns": strat_rets,
            "benchmark_returns": bench_rets_aligned,
            "close": close,
            "bench_close": bench_close,
            "holdings_history": holdings_history,
            "trades": port.trades,
            "warnings": strat.get_warnings(),
            "tickers": tickers,
        }

    def _get_universe(self, config: StrategyConfig) -> list[str]:
        if config.custom_tickers:
            return [t.strip().upper() for t in config.custom_tickers if t.strip()]
        universe = config.universe
        if "," in universe:
            return [t.strip().upper() for t in universe.split(",") if t.strip()]
        # sp500
        return self.provider.get_universe("sp500")
