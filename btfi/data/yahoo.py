from __future__ import annotations
import time
from typing import List
import pandas as pd
import yfinance as yf
from btfi.data.provider import DataProvider
from btfi.data.cache import Cache
from btfi.data.validation import validate_prices

# S&P 500 current constituents fallback (static list truncated for demo, full list fetched live when possible)
# We store ~50 tickers for offline/demo; live fetch via Wikipedia when online
FALLBACK_SP500 = ["AAPL","MSFT","NVDA","AMZN","META","GOOGL","BRK-B","AVGO","LLY","JPM","UNH","V","MA","PG","HD","COST","XOM","JNJ","ABBV","CRM","BAC","WMT","CVX","KO","NFLX","ORCL","MRK","PEP","TMO","ACN","CSCO","MCD","LIN","ABT","ADBE","DIS","DHR","AMD","WFC","TXN","QCOM","VZ","NEE","PM","INTU","AMGN","UNP","RTX","HON","CAT","GS","SPG","LOW","BKNG","EL","BA","BLK"]

class YahooFinanceProvider(DataProvider):
    def __init__(self, cache: Cache | None = None, enable_cache: bool = True):
        self.cache = cache or Cache()
        self.enable_cache = enable_cache

    def get_prices(self, tickers: List[str], start: str, end: str, auto_adjust: bool = False) -> pd.DataFrame:
        # Check cache first - try bulk path
        if self.enable_cache:
            cached = self.cache.bulk_get_prices(tickers, start, end)
            # If we have cached data, we still want to verify coverage; for simplicity if cached exists and we are offline, use it
            # But if not fully cached, we proceed to download
            pass

        # Use yfinance bulk download for efficiency
        try:
            data = yf.download(tickers, start=start, end=end, auto_adjust=auto_adjust, progress=False, group_by='ticker', threads=True)
            if data.empty:
                raise ValueError("No price data returned from yfinance")
        except Exception as e:
            # fallback to cache if download fails
            if self.enable_cache:
                # try individual cached files
                frames = {}
                for t in tickers:
                    df = self.cache.get(t, "prices")
                    if df is not None:
                        frames[t] = df
                if frames:
                    # combine into wide format mimicking yfinance structure
                    # For single ticker case yfinance returns flat; we normalize to multi-column
                    # Return concatenated dict-like: but for engine we handle both
                    # We'll return a dict of DataFrames? Instead return wide DataFrame with tickers as columns
                    # Simplistic: return first ticker's data if single
                    if len(tickers) == 1:
                        return frames[tickers[0]]
                    # Build wide: create MultiIndex columns
                    # Collect Close prices into panel
                    all_close = pd.DataFrame({t: df["Close"] if "Close" in df.columns else df.iloc[:, 3] for t, df in frames.items()})
                    all_close.columns = pd.MultiIndex.from_product([all_close.columns, ["Close"]])
                    return all_close
            raise

        # Cache individual tickers
        if self.enable_cache:
            try:
                if len(tickers) == 1:
                    # data is flat DataFrame
                    self.cache.put(tickers[0], "prices", data, start, end)
                else:
                    for t in tickers:
                        try:
                            sub = data[t] if t in data.columns.get_level_values(0) else None
                            if sub is not None and not sub.empty:
                                self.cache.put(t, "prices", sub, start, end)
                        except Exception:
                            continue
            except Exception:
                pass

        validate_prices(data if len(tickers)==1 else data)
        return data

    def get_dividends(self, ticker: str) -> pd.Series:
        if self.enable_cache:
            c = self.cache.get(ticker, "dividends")
            if c is not None:
                return c
        try:
            tk = yf.Ticker(ticker)
            s = tk.dividends
            if self.enable_cache and s is not None and not s.empty:
                self.cache.put(ticker, "dividends", s)
            return s if s is not None else pd.Series(dtype=float)
        except Exception:
            return pd.Series(dtype=float)

    def get_splits(self, ticker: str) -> pd.Series:
        if self.enable_cache:
            c = self.cache.get(ticker, "splits")
            if c is not None:
                return c
        try:
            tk = yf.Ticker(ticker)
            s = tk.splits
            if self.enable_cache and s is not None and not s.empty:
                self.cache.put(ticker, "splits", s)
            return s if s is not None else pd.Series(dtype=float)
        except Exception:
            return pd.Series(dtype=float)

    def get_info(self, ticker: str) -> dict:
        if self.enable_cache:
            c = self.cache.get(ticker, "info")
            if c is not None:
                return c
        try:
            tk = yf.Ticker(ticker)
            info = tk.info or {}
            if self.enable_cache and info:
                self.cache.put(ticker, "info", info)
            return info
        except Exception:
            return {}

    def get_fundamentals(self, ticker: str) -> dict:
        if self.enable_cache:
            c = self.cache.get(ticker, "fundamentals")
            if c is not None and isinstance(c, pd.DataFrame) and not c.empty:
                return {"cached": True, "data": c}
        try:
            tk = yf.Ticker(ticker)
            fin = {}
            try:
                fin["financials"] = tk.financials
            except Exception:
                fin["financials"] = pd.DataFrame()
            try:
                fin["balance_sheet"] = tk.balance_sheet
            except Exception:
                fin["balance_sheet"] = pd.DataFrame()
            try:
                fin["cashflow"] = tk.cashflow
            except Exception:
                fin["cashflow"] = pd.DataFrame()
            return fin
        except Exception:
            return {}

    def get_universe(self, universe: str = "sp500") -> list[str]:
        if universe == "sp500":
            # Try to fetch live S&P 500 from Wikipedia
            try:
                import requests
                url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
                tables = pd.read_html(url)
                if tables:
                    df = tables[0]
                    # Symbol column may be 'Symbol'
                    col = "Symbol" if "Symbol" in df.columns else df.columns[0]
                    tickers = df[col].astype(str).str.replace(".", "-", regex=False).str.strip().tolist()
                    tickers = [t for t in tickers if t and t != "nan"][:505]
                    if len(tickers) > 400:
                        return tickers
            except Exception:
                pass
            return FALLBACK_SP500
        # custom comma-separated
        if "," in universe:
            return [t.strip().upper() for t in universe.split(",") if t.strip()]
        return [universe]
