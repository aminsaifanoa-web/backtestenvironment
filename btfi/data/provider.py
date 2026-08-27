from __future__ import annotations
from abc import ABC, abstractmethod
import pandas as pd

class DataProvider(ABC):
    """Abstract data provider. All yfinance specifics live in YahooFinanceProvider."""

    @abstractmethod
    def get_prices(self, tickers: list[str], start: str, end: str, auto_adjust: bool = False) -> pd.DataFrame:
        """Return MultiIndex or single DataFrame of OHLCV. Columns: Open, High, Low, Close, Adj Close, Volume"""
        ...

    @abstractmethod
    def get_dividends(self, ticker: str) -> pd.Series:
        ...

    @abstractmethod
    def get_splits(self, ticker: str) -> pd.Series:
        ...

    @abstractmethod
    def get_info(self, ticker: str) -> dict:
        ...

    @abstractmethod
    def get_fundamentals(self, ticker: str) -> dict:
        """Return dict with financials, balance_sheet, cashflow if available."""
        ...

    @abstractmethod
    def get_universe(self, universe: str = "sp500") -> list[str]:
        """Return list of tickers for universe. 'sp500' or 'custom'."""
        ...
