from __future__ import annotations
from btfi.strategies.base import StrategyConfig
from btfi.strategies.builtins import ValueStrategy, PriceMomentumStrategy, MultifactorStrategy

# Catalog of built-in strategy templates
BUILTIN_STRATEGIES = [
    # Passive
    {"id": "spy_buy_hold", "name": "S&P 500 Buy & Hold (SPY)", "category": "Passive", "metric": "market_cap", "description": "Buy SPY and hold", "rebalance": "annual", "template": "passive"},
    {"id": "equal_weight_sp500", "name": "Equal-Weight S&P 500", "category": "Passive", "metric": "market_cap", "description": "Equal weight all S&P 500", "rebalance": "quarterly", "weighting": "equal", "top_n": 500, "template": "equal_weight"},
    {"id": "dca_monthly", "name": "Monthly DCA into SPY", "category": "Passive", "metric": "market_cap", "description": "Dollar cost averaging monthly", "rebalance": "monthly", "template": "dca"},
    {"id": "dca_quarterly", "name": "Quarterly DCA into SPY", "category": "Passive", "metric": "market_cap", "description": "Dollar cost averaging quarterly", "rebalance": "quarterly", "template": "dca"},
    # Value
    {"id": "low_pe", "name": "Lowest P/E — Top 20", "category": "Value", "metric": "pe", "top_n": 20, "weighting": "equal", "rebalance": "annual"},
    {"id": "low_pb", "name": "Lowest P/B — Top 20", "category": "Value", "metric": "pb", "top_n": 20, "weighting": "equal", "rebalance": "annual"},
    {"id": "high_fcf_yield", "name": "Highest FCF Yield — Top 20", "category": "Value", "metric": "fcf_yield", "top_n": 20, "weighting": "equal", "rebalance": "annual"},
    {"id": "high_earnings_yield", "name": "Highest Earnings Yield — Top 20", "category": "Value", "metric": "earnings_yield", "top_n": 20, "weighting": "equal", "rebalance": "annual"},
    {"id": "high_dividend_yield", "name": "Highest Dividend Yield — Top 20", "category": "Value", "metric": "dividend_yield", "top_n": 20, "weighting": "equal", "rebalance": "annual"},
    {"id": "low_ev_ebitda", "name": "Lowest EV/EBITDA — Top 20", "category": "Value", "metric": "ev_ebitda", "top_n": 20, "weighting": "equal", "rebalance": "annual"},
    # Quality
    {"id": "high_roe", "name": "Highest ROE — Top 20", "category": "Quality", "metric": "roe", "top_n": 20, "weighting": "equal", "rebalance": "annual"},
    {"id": "high_roic", "name": "Highest ROIC — Top 20", "category": "Quality", "metric": "roic", "top_n": 20, "weighting": "equal", "rebalance": "annual"},
    {"id": "high_margins", "name": "Highest Margins — Top 20", "category": "Quality", "metric": "roe", "top_n": 20, "weighting": "equal", "rebalance": "annual"},
    {"id": "low_leverage", "name": "Lowest Leverage — Top 20", "category": "Quality", "metric": "pb", "top_n": 20, "weighting": "equal", "rebalance": "annual"},
    # Momentum
    {"id": "mom_3m", "name": "3-Month Momentum — Top 20", "category": "Momentum", "metric": "momentum_3m", "top_n": 20, "weighting": "equal", "rebalance": "quarterly"},
    {"id": "mom_6m", "name": "6-Month Momentum — Top 20", "category": "Momentum", "metric": "momentum_6m", "top_n": 20, "weighting": "equal", "rebalance": "quarterly"},
    {"id": "mom_12m", "name": "12-Month Momentum — Top 20", "category": "Momentum", "metric": "momentum_12m", "top_n": 20, "weighting": "equal", "rebalance": "quarterly"},
    {"id": "mom_12_1", "name": "12-1 Momentum — Top 20", "category": "Momentum", "metric": "momentum_12_1", "top_n": 20, "weighting": "equal", "rebalance": "monthly"},
    # Growth
    {"id": "high_revenue_growth", "name": "Highest Revenue Growth — Top 20", "category": "Growth", "metric": "revenue_growth", "top_n": 20, "weighting": "equal", "rebalance": "annual"},
    {"id": "high_earnings_growth", "name": "Highest Earnings Growth — Top 20", "category": "Growth", "metric": "earnings_growth", "top_n": 20, "weighting": "equal", "rebalance": "annual"},
    # Contrarian
    {"id": "worst_last_year", "name": "Previous Year's Worst Performers — Top 20", "category": "Contrarian", "metric": "momentum_12m", "top_n": 20, "weighting": "equal", "rebalance": "annual", "extra_params": {"contrarian": True}},
    {"id": "largest_drawdowns", "name": "Largest Drawdowns — Top 20", "category": "Contrarian", "metric": "momentum_12m", "top_n": 20, "weighting": "equal", "rebalance": "annual", "extra_params": {"contrarian": True}},
    # Multifactor
    {"id": "value_quality", "name": "Value + Quality (50/50)", "category": "Multifactor", "metric": "multifactor", "formula": "0.5*rank(fcf_yield)+0.5*rank(roic)", "top_n": 20, "weighting": "equal", "rebalance": "annual"},
    {"id": "value_momentum", "name": "Value + Momentum (50/50)", "category": "Multifactor", "metric": "multifactor", "formula": "0.5*rank(fcf_yield)+0.5*rank(momentum_12m)", "top_n": 20, "weighting": "equal", "rebalance": "quarterly"},
    {"id": "quality_momentum", "name": "Quality + Momentum (50/50)", "category": "Multifactor", "metric": "multifactor", "formula": "0.5*rank(roic)+0.5*rank(momentum_12m)", "top_n": 20, "weighting": "equal", "rebalance": "quarterly"},
    {"id": "value_quality_momentum", "name": "Value + Quality + Momentum", "category": "Multifactor", "metric": "multifactor", "formula": "0.33*rank(fcf_yield)+0.33*rank(roic)+0.34*rank(momentum_12m)", "top_n": 20, "weighting": "equal", "rebalance": "quarterly"},
    # Weird
    {"id": "largest_companies", "name": "Buy Largest Companies — Top 20", "category": "Weird", "metric": "market_cap", "top_n": 20, "weighting": "equal", "rebalance": "annual", "extra_params": {"direction": "largest"}},
    {"id": "smallest_companies", "name": "Buy Smallest Companies — Top 20", "category": "Weird", "metric": "market_cap", "top_n": 20, "weighting": "equal", "rebalance": "annual", "extra_params": {"direction": "smallest"}},
    {"id": "low_vol", "name": "Lowest Volatility — Top 20", "category": "Weird", "metric": "volatility", "top_n": 20, "weighting": "equal", "rebalance": "quarterly"},
    {"id": "random_portfolio", "name": "Random Portfolio — 20 stocks", "category": "Weird", "metric": "market_cap", "top_n": 20, "weighting": "equal", "rebalance": "annual", "extra_params": {"weird": "random"}},
    {"id": "alphabetical", "name": "Alphabetical Ticker Strategy — Top 20", "category": "Weird", "metric": "market_cap", "top_n": 20, "weighting": "equal", "rebalance": "annual", "extra_params": {"weird": "alphabetical"}},
    {"id": "cash_holdings", "name": "Highest Cash Holdings — Top 20", "category": "Weird", "metric": "market_cap", "top_n": 20, "weighting": "equal", "rebalance": "annual", "extra_params": {"weird": "random"}},
]

def list_strategies(category: str | None = None):
    if category:
        return [s for s in BUILTIN_STRATEGIES if s["category"].lower() == category.lower()]
    return BUILTIN_STRATEGIES

def get_strategy_template(strategy_id: str) -> dict | None:
    for s in BUILTIN_STRATEGIES:
        if s["id"] == strategy_id:
            return s
    return None

def make_config_from_template(template_id: str, overrides: dict | None = None) -> StrategyConfig:
    t = get_strategy_template(template_id)
    if not t:
        raise ValueError(f"Unknown strategy template: {template_id}")
    cfg = StrategyConfig(
        name=t["name"],
        description=t.get("description",""),
        category=t.get("category","Experimental"),
        metric=t.get("metric","momentum_12m"),
        formula=t.get("formula"),
        top_n=t.get("top_n",20),
        weighting=t.get("weighting","equal"),
        rebalance=t.get("rebalance","annual"),
        extra_params=t.get("extra_params",{}).copy(),
    )
    if overrides:
        for k, v in overrides.items():
            if hasattr(cfg, k):
                setattr(cfg, k, v)
            else:
                cfg.extra_params[k] = v
    return cfg

def instantiate_strategy(config: StrategyConfig):
    # Choose class based on formula or metric
    if config.formula:
        return MultifactorStrategy(config)
    if config.metric.startswith("momentum") or config.metric in ("volatility",):
        # map lookback
        lb_map = {"momentum_3m":63, "momentum_6m":126, "momentum_12m":252, "momentum_12_1":252}
        lb = lb_map.get(config.metric, 252)
        skip = 21 if config.metric == "momentum_12_1" else 0
        # For contrarian, invert momentum ranking
        s = PriceMomentumStrategy(config, lb, skip)
        # wrap select for contrarian: pick bottom instead of top
        if config.extra_params.get("contrarian"):
            orig_select = s.select
            def contrarian_select(ranked, cfg):
                # For contrarian pick bottom performers: reverse ranked
                # ranked is ascending (lower rank = higher momentum). Worst performers have high signal (less negative)
                # So pick tail
                cfg2 = StrategyConfig(**{**cfg.__dict__, "selection_mode": "bottom_n"})
                return orig_select(ranked, cfg2)
            s.select = contrarian_select
        return s
    # value/quality etc
    return ValueStrategy(config)
