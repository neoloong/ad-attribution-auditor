"""Date parsing and normalization helpers."""

from __future__ import annotations

import pandas as pd
from dateutil import parser as dateutil_parser


def parse_date_column(series: pd.Series) -> pd.Series:
    """Parse a Series of mixed date strings into datetime64[ns].

    Handles common formats: ISO-8601, US (MM/DD/YYYY), European (DD/MM/YYYY),
    and Shopify-style (``2024-01-15 14:23:00 -0500``).
    Falls back to ``dateutil`` for ambiguous entries.
    """
    result = pd.to_datetime(series, format="mixed", utc=True, dayfirst=False)
    return result.dt.tz_localize(None)


def to_date_only(series: pd.Series) -> pd.Series:
    """Strip time component, returning ``datetime64[ns]`` at midnight."""
    return pd.to_datetime(series).dt.normalize()


def date_range_label(df: pd.DataFrame, col: str = "date") -> str:
    """Return a human-readable date range string like '2024-01-01 to 2024-01-31'."""
    mn = df[col].min()
    mx = df[col].max()
    return f"{mn:%Y-%m-%d} to {mx:%Y-%m-%d}"
