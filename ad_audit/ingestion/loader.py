"""CSV loading with encoding detection."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import IO

import chardet
import pandas as pd


def detect_encoding(raw_bytes: bytes, sample_size: int = 10_000) -> str:
    """Return the detected encoding for *raw_bytes*."""
    result = chardet.detect(raw_bytes[:sample_size])
    return result.get("encoding", "utf-8") or "utf-8"


def load_csv(source: str | Path | IO | BytesIO) -> pd.DataFrame:
    """Read a CSV into a DataFrame, auto-detecting encoding.

    *source* can be a file path, an open binary stream, or a ``BytesIO``.
    """
    if isinstance(source, (str, Path)):
        raw = Path(source).read_bytes()
    elif isinstance(source, BytesIO):
        raw = source.getvalue()
    else:
        raw = source.read()

    encoding = detect_encoding(raw)
    return pd.read_csv(BytesIO(raw), encoding=encoding)
