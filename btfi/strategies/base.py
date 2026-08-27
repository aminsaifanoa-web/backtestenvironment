from __future__ import annotations
from dataclasses import dataclass, field
from typing import Literal, Optional
import pandas as pd
import numpy as np

Weighting = Literal["equal", "market_cap", "inverse_vol", "score"]
RebalanceFreq = Literal["daily", "weekly", "monthly", "quarterly", "semiannual", "annual"]
SelectionMode = Literal["top_n", "top_pct", "bottom_n", "bottom_pct"]

@dataclass
class StrategyConfig:
    name: str
    description: str = ""
    category: str = "Experimental"
    universe: str = "sp500"  # sp500 or comma-separated tickers
    custom_tickers: list[str] | None = None
    metric: str = "momentum_12m"
    formula: str | None = None  # for custom multi-factor
    top_n: int | None = 20
    top_pct: float | None = None
    selection_mode: SelectionMode = "top_n"
    weighting: Weighting = "equal"
    rebalance: RebalanceFreq = "annual"
    transaction_cost_bps: float = 10.0
    slippage_bps: float = 5.0
    start_date: str = "2010-01-01"
    end_date: str = "2024-12-31"
    benchmark: str = "SPY"
    # for weird strategies
    extra_params: dict = field(default_factory=dict)

    def to_dict(self):
        return self.__dict__.copy()

class Strategy:
    """Base strategy template. Subclasses implement signal/rank/select/weight."""

    def __init__(self, config: StrategyConfig):
        self.config = config

    @property
    def name(self) -> str:
        return self.config.name

    @property
    def description(self) -> str:
        return self.config.description

    def universe(self, provider) -> list[str]:
        if self.config.custom_tickers:
            return self.config.custom_tickers
        return provider.get_universe(self.config.universe)

    def compute_signals(self, prices: pd.DataFrame, info_map: dict | None = None) -> pd.DataFrame:
        """Return DataFrame: index=date, columns=ticker, values=signal score. Lower is 'cheaper' for value, higher is 'better' for quality."""
        raise NotImplementedError

    def rank(self, signals: pd.DataFrame) -> pd.DataFrame:
        # rank ascending (1=best). For signals where higher is better, rank descending; we handle sign in signal generation
        return signals.rank(axis=1, method="average", ascending=True)

    def select(self, ranked: pd.Series, config: StrategyConfig) -> list[str]:
        """Given a cross-sectional ranked series at a rebalance date, select tickers."""
        # Drop NaNs
        s = ranked.dropna().sort_values()
        n = len(s)
        if n == 0:
            return []
        if config.selection_mode == "top_n":
            k = config.top_n or 20
            return s.head(min(k, n)).index.tolist()
        elif config.selection_mode == "bottom_n":
            k = config.top_n or 20
            return s.tail(min(k, n)).index.tolist()
        elif config.selection_mode == "top_pct":
            pct = config.top_pct or 0.1
            k = max(1, int(n * pct))
            return s.head(k).index.tolist()
        elif config.selection_mode == "bottom_pct":
            pct = config.top_pct or 0.1
            k = max(1, int(n * pct))
            return s.tail(k).index.tolist()
        return s.head(20).index.tolist()

    def weight(self, selected: list[str], signals: pd.Series | None = None, prices: pd.DataFrame | None = None, info_map: dict | None = None) -> dict[str, float]:
        n = len(selected)
        if n == 0:
            return {}
        w = self.config.weighting
        if w == "equal":
            return {t: 1.0/n for t in selected}
        elif w == "market_cap" and info_map:
            caps = {t: max(info_map.get(t, {}).get("marketCap", 0) or 0, 1) for t in selected}
            total = sum(caps.values())
            if total == 0:
                return {t: 1.0/n for t in selected}
            return {t: caps[t]/total for t in selected}
        elif w == "inverse_vol" and prices is not None:
            # inverse 60d volatility
            vols = {}
            for t in selected:
                try:
                    # prices may be wide DataFrame; extract series
                    if isinstance(prices, pd.DataFrame) and t in prices.columns.get_level_values(0) if isinstance(prices.columns, pd.MultiIndex) else t in prices.columns:
                        if isinstance(prices.columns, pd.MultiIndex):
                            col = prices[t]["Close"] if t in prices.columns.get_level_values(0) else None
                        else:
                            col = prices[t]
                        if col is not None:
                            rets = col.pct_change().dropna().tail(60)
                            vols[t] = rets.std() or 0.01
                        else:
                            vols[t] = 0.02
                    else:
                        vols[t] = 0.02
                except Exception:
                    vols[t] = 0.02
            inv = {t: 1/max(v, 0.001) for t, v in vols.items()}
            tot = sum(inv.values())
            return {t: inv[t]/tot for t in selected}
        elif w == "score" and signals is not None:
            # weight proportional to inverse rank or signal strength
            vals = signals.reindex(selected).dropna()
            if vals.empty:
                return {t: 1.0/n for t in selected}
            # convert rank to score: lower rank => higher weight
            # use 1/rank
            inv = {t: 1/max(float(vals[t]), 0.5) for t in selected if t in vals.index}
            # fill missing with equal
            for t in selected:
                if t not in inv:
                    inv[t] = 1.0
            tot = sum(inv.values())
            return {t: inv[t]/tot for t in selected}
        return {t: 1.0/n for t in selected}

    def rebalance_dates(self, all_dates: pd.DatetimeIndex) -> pd.DatetimeIndex:
        freq_map = {
            "daily": "D",
            "weekly": "W",
            "monthly": "M",
            "quarterly": "Q",
            "semiannual": "6M",
            "annual": "A",
        }
        # Instead of resample, we pick dates at frequency
        rule = self.config.rebalance
        if rule == "daily":
            return all_dates
        elif rule == "weekly":
            # every Monday
            return all_dates[all_dates.weekday == 0]
        elif rule == "monthly":
            return all_dates[all_dates.is_month_end]
        elif rule == "quarterly":
            return all_dates[all_dates.is_quarter_end]
        elif rule == "semiannual":
            # June and Dec month end
            return all_dates[(all_dates.month.isin([6,12])) & all_dates.is_month_end]
        elif rule == "annual":
            return all_dates[all_dates.is_year_end]
        return all_dates[all_dates.is_year_end]

    def get_warnings(self) -> list[str]:
        warnings = []
        if self.config.universe == "sp500":
            warnings.append("⚠ Historical constituent data unavailable. Survivorship bias may materially affect results. Using current S&P 500 constituents as historical universe.")
        fundamentals_metrics = {"pe","pb","ev_ebitda","ev_ebit","fcf_yield","earnings_yield","dividend_yield","roe","roic","revenue_growth","earnings_growth","market_cap"}
        if self.config.metric in fundamentals_metrics or (self.config.formula and any(m in self.config.formula for m in fundamentals_metrics)):
            warnings.append("⚠ Potential look-ahead bias: historical publication dates are unavailable for this fundamental dataset via yfinance.")
        return warnings
