from __future__ import annotations
import pandas as pd
import numpy as np

class Portfolio:
    """Tracks holdings, cash, and transaction costs. Simple accounting."""
    def __init__(self, initial_capital: float = 10000.0, transaction_cost_bps: float = 10, slippage_bps: float = 5):
        self.initial_capital = initial_capital
        self.cash = initial_capital
        self.holdings: dict[str, float] = {}  # ticker -> shares
        self.transaction_cost_bps = transaction_cost_bps
        self.slippage_bps = slippage_bps
        self.trades: list[dict] = []

    def total_cost_bps(self) -> float:
        return self.transaction_cost_bps + self.slippage_bps

    def value(self, prices: dict[str, float]) -> float:
        mv = sum(self.holdings.get(t, 0) * prices.get(t, 0) for t in self.holdings)
        return mv + self.cash

    def holdings_weights(self, prices: dict[str, float]) -> dict[str, float]:
        total = self.value(prices)
        if total == 0:
            return {}
        return {t: (self.holdings.get(t,0)*prices.get(t,0))/total for t in self.holdings}

    def rebalance_to_target(self, target_weights: dict[str, float], prices: dict[str,float], date: pd.Timestamp):
        """Generate trades to reach target weights."""
        total = self.value(prices)
        if total <= 0 or not prices:
            return
        # Calculate target shares
        target_shares = {}
        for t, w in target_weights.items():
            px = prices.get(t)
            if px and px > 0:
                target_shares[t] = (total * w) / px

        # Sell tickers not in target
        for t in list(self.holdings.keys()):
            if t not in target_shares:
                target_shares[t] = 0

        # Execute sells first, then buys (to free cash)
        sells = {t: s for t, s in target_shares.items() if s < self.holdings.get(t, 0) - 1e-9}
        buys = {t: s for t, s in target_shares.items() if s >= self.holdings.get(t, 0) - 1e-9}
        for phase in [sells, buys]:
            for t, tgt_shares in phase.items():
                cur = self.holdings.get(t, 0)
                delta = tgt_shares - cur
                if abs(delta) < 1e-6:
                    continue
                px = prices.get(t, 0)
                if px <= 0:
                    continue
                trade_value = abs(delta) * px
                cost = trade_value * self.total_cost_bps() / 10000.0
                if delta > 0:
                    needed = delta * px + cost
                    if needed > self.cash + 1e-6:
                        available = self.cash
                        max_shares = available / (px * (1 + self.total_cost_bps()/10000)) if px > 0 else 0
                        delta = max_shares
                        trade_value = delta * px
                        cost = trade_value * self.total_cost_bps()/10000
                        if delta < 1e-6:
                            continue
                        self.cash -= (trade_value + cost)
                        self.holdings[t] = cur + delta
                    else:
                        self.cash -= (trade_value + cost)
                        self.holdings[t] = tgt_shares
                else:
                    proceeds = (-delta) * px - cost
                    self.cash += proceeds
                    if abs(tgt_shares) < 1e-6:
                        self.holdings.pop(t, None)
                    else:
                        self.holdings[t] = tgt_shares
                self.trades.append({"date": date, "ticker": t, "delta_shares": float(delta), "price": float(px), "cost": float(cost)})

        # Handle dividends: assumed added to cash externally prior to rebalance; portfolio just tracks cash
