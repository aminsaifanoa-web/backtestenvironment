from __future__ import annotations
import os
from pathlib import Path
from datetime import datetime, timezone
import pandas as pd

try:
    import duckdb
    HAS_DUCKDB = True
except Exception:
    HAS_DUCKDB = False

CACHE_DIR_ENV = os.getenv("BTFI_CACHE_DIR", "./data/cache")

class Cache:
    """Parquet + DuckDB cache. Workflow: check cache -> download -> validate -> cache -> use."""

    def __init__(self, cache_dir: str | Path | None = None):
        self.cache_dir = Path(cache_dir or CACHE_DIR_ENV)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.duckdb_path = self.cache_dir / "btfi.duckdb"
        self._con = None
        if HAS_DUCKDB:
            try:
                self._con = duckdb.connect(str(self.duckdb_path))
                self._con.execute("CREATE TABLE IF NOT EXISTS cache_meta (ticker VARCHAR, dataset VARCHAR, start VARCHAR, end VARCHAR, rows INTEGER, last_updated VARCHAR, source VARCHAR)")
            except Exception:
                self._con = None

    def _parquet_path(self, ticker: str, dataset: str) -> Path:
        safe = ticker.replace(".", "_").replace("/", "_")
        return self.cache_dir / f"{safe}__{dataset}.parquet"

    def get(self, ticker: str, dataset: str) -> pd.DataFrame | pd.Series | dict | None:
        p = self._parquet_path(ticker, dataset)
        if not p.exists():
            return None
        try:
            if dataset in ("prices", "prices_bulk"):
                return pd.read_parquet(p)
            elif dataset in ("dividends", "splits"):
                s = pd.read_parquet(p)
                # stored as DataFrame with one column
                if isinstance(s, pd.DataFrame) and s.shape[1] == 1:
                    return s.iloc[:, 0]
                return s
            else:
                # info/fundamentals as parquet with single row? fallback to reading
                df = pd.read_parquet(p)
                if dataset == "info":
                    return df.iloc[0].to_dict() if not df.empty else None
                return df
        except Exception:
            return None

    def put(self, ticker: str, dataset: str, data, start: str = "", end: str = ""):
        p = self._parquet_path(ticker, dataset)
        try:
            if isinstance(data, pd.DataFrame):
                data.to_parquet(p, index=True)
            elif isinstance(data, pd.Series):
                data.to_frame(name="value").to_parquet(p, index=True)
            elif isinstance(data, dict):
                pd.DataFrame([data]).to_parquet(p, index=False)
            else:
                pd.DataFrame(data).to_parquet(p)
            rows = len(data) if hasattr(data, "__len__") else 1
            if self._con is not None:
                try:
                    self._con.execute("DELETE FROM cache_meta WHERE ticker=? AND dataset=?", [ticker, dataset])
                    self._con.execute("INSERT INTO cache_meta VALUES (?, ?, ?, ?, ?, ?, ?)",
                                      [ticker, dataset, start, end, int(rows), datetime.now(timezone.utc).isoformat(), "yfinance"])
                except Exception:
                    pass
        except Exception as e:
            # fallback silently
            pass

    def bulk_get_prices(self, tickers: list[str], start: str, end: str) -> pd.DataFrame | None:
        # attempt to load bulk parquet if exists
        # For simplicity, try individual files and concat
        frames = []
        for t in tickers:
            df = self.get(t, "prices")
            if df is not None and not df.empty:
                # filter dates
                try:
                    df.index = pd.to_datetime(df.index)
                    mask = (df.index >= pd.to_datetime(start)) & (df.index <= pd.to_datetime(end))
                    sub = df.loc[mask]
                    if not sub.empty:
                        frames.append(sub.assign(_ticker=t))
                except Exception:
                    continue
        if not frames:
            return None
        # return concatenated long format? For provider we need pivot
        # Simpler: return None to trigger download if incomplete
        # Check if we have all tickers
        if len(frames) < len(tickers) * 0.5:  # less than half covered
            return None
        return pd.concat(frames)

    def metadata(self) -> pd.DataFrame:
        if self._con is not None:
            try:
                return self._con.execute("SELECT * FROM cache_meta ORDER BY last_updated DESC").fetchdf()
            except Exception:
                pass
        # fallback scan filesystem
        rows = []
        for f in self.cache_dir.glob("*.parquet"):
            try:
                stat = f.stat()
                rows.append({"file": f.name, "size_kb": round(stat.st_size/1024,1), "modified": datetime.fromtimestamp(stat.st_mtime).isoformat()})
            except Exception:
                continue
        return pd.DataFrame(rows)

    def clear(self, ticker: str | None = None):
        if ticker:
            for f in self.cache_dir.glob(f"{ticker}__*"):
                try:
                    f.unlink()
                except Exception:
                    pass
        else:
            for f in self.cache_dir.glob("*.parquet"):
                try:
                    f.unlink()
                except Exception:
                    pass
            if self._con is not None:
                try:
                    self._con.execute("DELETE FROM cache_meta")
                except Exception:
                    pass

    def cache_size_mb(self) -> float:
        total = sum(f.stat().st_size for f in self.cache_dir.glob("*.parquet") if f.exists())
        return round(total / (1024*1024), 2)
