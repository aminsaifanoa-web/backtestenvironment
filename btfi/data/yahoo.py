from __future__ import annotations
import time
from typing import List
import pandas as pd
import yfinance as yf
from btfi.data.provider import DataProvider
from btfi.data.cache import Cache
from btfi.data.validation import validate_prices

# S&P 500 current constituents fallback (static ~120 large-cap proxy; full 500 fetched live when Wikipedia available)
FALLBACK_SP500 = ["AAPL","MSFT","NVDA","AMZN","META","GOOGL","BRK-B","AVGO","LLY","JPM","UNH","V","MA","PG","HD","COST","XOM","JNJ","ABBV","CRM","BAC","WMT","CVX","KO","NFLX","ORCL","MRK","PEP","TMO","ACN","CSCO","MCD","LIN","ABT","ADBE","DIS","DHR","AMD","WFC","TXN","QCOM","VZ","NEE","PM","INTU","AMGN","UNP","RTX","HON","CAT","GS","SPG","LOW","BKNG","EL","BA","BLK","AXP","BLK","BSX","CHTR","CI","CL","CMCSA","COF","COP","COST","CRM","CSCO","CVS","CVX","D","DE","DG","DHR","DIS","DUK","ECL","EL","EMR","EXC","F","FDX","GD","GE","GILD","GM","GOOGL","GPN","HCA","HD","HON","IBM","ICE","INTC","INTU","ISRG","ITW","JCI","JNJ","JPM","KHC","KO","LIN","LLY","LMT","LOW","LRCX","MA","MCD","MDLZ","MDT","META","MET","MMC","MO","MRK","MS","MSFT","NEE","NFLX","NKE","NOW","NVDA","ORCL","PEP","PFE","PG","PGR","PH","PM","PSA","QCOM","REGN","RTX","SCHW","SHW","SO","SPG","SYK","T","TGT","TMO","TXN","UNH","UNP","UPS","V","VZ","WFC","WM","WMT","XOM","ZTS","ADP","ADI","ADSK","AON","APH","AZO","BDX","BIIB","CB","CCI","CMG","DHI","EA","ECL","ETN","EW","EXR","FIS","FTNT","GWW","HUM","KLAC","MAR","MCK","MCO","MLM","MNST","MSCI","NSC","NTAP","ORLY","OTIS","PAYX","PCAR","ROP","ROST","SBAC","SBUX","SPGI","TT","VRSK","WST","YUM","A","AAL","AIG","ALL","AMAT","AMP","AMZN","AVB","AVGO","AXP","BA","BAC","BDX","BEN","BF-B","BG"]

class YahooFinanceProvider(DataProvider):
    def __init__(self, cache: Cache | None = None, enable_cache: bool = True):
        self.cache = cache or Cache()
        self.enable_cache = enable_cache

    def get_prices(self, tickers: List[str], start: str, end: str, auto_adjust: bool = False) -> pd.DataFrame:
        # Fast cache path: if all tickers cached and cover requested range, return immediately
        if self.enable_cache:
            frames = {}
            all_cached = True
            for t in tickers:
                df = self.cache.get(t, "prices")
                if df is None or df.empty:
                    all_cached = False
                    break
                try:
                    # check date coverage
                    idx = pd.to_datetime(df.index)
                    if idx.min() > pd.to_datetime(start) + pd.Timedelta(days=30) or idx.max() < pd.to_datetime(end) - pd.Timedelta(days=30):
                        all_cached = False
                        break
                    frames[t] = df
                except Exception:
                    all_cached = False
                    break
            if all_cached and frames:
                # reconstruct yfinance-like DataFrame with MultiIndex
                if len(tickers) == 1:
                    return frames[tickers[0]]
                # Build MultiIndex DataFrame
                try:
                    combined = pd.concat(frames, axis=1)
                    # combined has outer level ticker, inner OHLC columns
                    # Ensure order matches yfinance group_by ticker
                    return combined
                except Exception:
                    pass

        # Use yfinance bulk download for efficiency
        try:
            data = yf.download(tickers, start=start, end=end, auto_adjust=auto_adjust, progress=False, group_by='ticker', threads=False)
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
