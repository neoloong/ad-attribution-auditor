"""Email hashing utilities for privacy-safe matching."""

from __future__ import annotations

import hashlib

import pandas as pd


def hash_email(email: str) -> str:
    """Return a lowercase SHA-256 hex digest of a stripped, lowered email."""
    normalized = email.strip().lower()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def hash_email_series(series: pd.Series) -> pd.Series:
    """Hash an entire Series of email addresses. NaN stays NaN."""
    return series.dropna().map(hash_email).reindex(series.index)
