from __future__ import annotations
from dataclasses import dataclass
from datetime import date
from typing import Optional

@dataclass(frozen=True)
class PriceBar:
    ticker: str
    date: date
    open: float
    high: float
    low: float
    close: float
    adj_close: float
    volume: int

@dataclass
class DataWarning:
    code: str
    message: str
    severity: str = "warning"  # warning, critical

@dataclass
class CacheMetadata:
    ticker: str
    dataset: str
    start: str
    end: str
    rows: int
    last_updated: str
    source: str = "yfinance"

# Valid ranking metrics that can be supported by yfinance data
SUPPORTED_METRICS = [
    "pe",
    "pb",
    "ev_ebitda",
    "ev_ebit",
    "fcf_yield",
    "earnings_yield",
    "dividend_yield",
    "dividend_growth",
    "roe",
    "roic",
    "revenue_growth",
    "earnings_growth",
    "momentum_3m",
    "momentum_6m",
    "momentum_12m",
    "momentum_12_1",
    "volatility",
    "market_cap",
]

METRIC_LABELS = {
    "pe": "P/E",
    "pb": "P/B",
    "ev_ebitda": "EV/EBITDA",
    "ev_ebit": "EV/EBIT",
    "fcf_yield": "FCF Yield",
    "earnings_yield": "Earnings Yield",
    "dividend_yield": "Dividend Yield",
    "dividend_growth": "Dividend Growth",
    "roe": "ROE",
    "roic": "ROIC",
    "revenue_growth": "Revenue Growth",
    "earnings_growth": "Earnings Growth",
    "momentum_3m": "3M Momentum",
    "momentum_6m": "6M Momentum",
    "momentum_12m": "12M Momentum",
    "momentum_12_1": "12-1 Momentum",
    "volatility": "Volatility",
    "market_cap": "Market Cap",
}

# For formula parser
AVAILABLE_VARIABLES = SUPPORTED_METRICS + ["rank", "zscore", "percentile"]
