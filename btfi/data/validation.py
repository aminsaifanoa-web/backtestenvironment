from __future__ import annotations
import pandas as pd

def validate_prices(df: pd.DataFrame) -> list[str]:
    warnings = []
    if df.empty:
        warnings.append("Price data empty")
        return warnings
    # check for missing dates, duplicates
    if df.isnull().all().all():
        warnings.append("All values null")
    # duplicate index
    if df.index.duplicated().any():
        warnings.append("Duplicate dates detected; deduplicated")
    # gaps > 10 business days
    if isinstance(df.index, pd.DatetimeIndex) and len(df) > 5:
        gaps = df.index.to_series().diff().dt.days.fillna(0)
        if (gaps > 10).any():
            warnings.append("Large date gap detected (>10 days) - possible missing data or delisting")
    return warnings

def validate_fundamentals(info: dict) -> list[str]:
    warnings = []
    if not info:
        warnings.append("No fundamentals available for ticker")
    return warnings
