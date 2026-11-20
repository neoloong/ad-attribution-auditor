"""CSV loading with encoding detection."""

from __future__ import annotations

import csv
import io
from io import BytesIO
from pathlib import Path
from typing import IO

import chardet
import pandas as pd

from ad_audit.ingestion.validators import DEFAULT_SOURCE, InvalidInputError

FIELD_COUNT_GUIDANCE = (
    "This usually means a number with a thousands separator (e.g. 1,234) was "
    "written without quotes, so its comma split one value into two columns. "
    "Re-export with quoted numbers or with no thousands separators. If the file "
    "starts with report-title or date-range lines, delete them so the first line "
    "is the column header."
)


def detect_encoding(raw_bytes: bytes, sample_size: int = 10_000) -> str:
    """Return the detected encoding for *raw_bytes*.

    Bytes that contain non-ASCII and decode cleanly as UTF-8 are UTF-8:
    chardet alone guesses Windows-1252 for small UTF-8 files containing
    ``€`` / ``£`` / ``—`` and turns ``€12`` into ``â‚¬12``.  Pure-ASCII and
    non-UTF-8 files go through chardet exactly as before.
    """
    if not raw_bytes.isascii():
        try:
            raw_bytes.decode("utf-8")
        except UnicodeDecodeError:
            pass
        else:
            return "utf-8-sig" if raw_bytes.startswith(b"\xef\xbb\xbf") else "utf-8"
    result = chardet.detect(raw_bytes[:sample_size])
    return result.get("encoding", "utf-8") or "utf-8"


def field_count_errors(raw: bytes, encoding: str, source_name: str | None = None) -> list[str]:
    """Return one error per data line whose field count differs from the header.

    pandas silently tolerates some mismatches (if *every* data row has one
    extra field it turns the first column into the index and shifts all
    columns left), so the check runs before pandas sees the file.  Lines
    that are completely empty are skipped, as pandas skips them.  If the
    bytes cannot be decoded or tokenised here, the check is skipped and
    pandas' own behaviour (and errors) apply unchanged.
    """
    source = source_name or DEFAULT_SOURCE
    try:
        text = raw.decode(encoding)
        reader = csv.reader(io.StringIO(text, newline=""))
        header_len = None
        errors: list[str] = []
        for row in reader:
            if not row:
                continue
            if header_len is None:
                header_len = len(row)
                continue
            if len(row) != header_len:
                errors.append(
                    f"{source}: line {reader.line_num}: {len(row)} fields but the header has "
                    f"{header_len}. {FIELD_COUNT_GUIDANCE}"
                )
    except (UnicodeDecodeError, LookupError, csv.Error):
        return []
    return errors


def load_csv(source: str | Path | IO | BytesIO, source_name: str | None = None) -> pd.DataFrame:
    """Read a CSV into a DataFrame, auto-detecting encoding.

    *source* can be a file path, an open binary stream, or a ``BytesIO``.

    Only truly empty cells become NaN.  Text such as ``N/A``, ``null`` or
    ``nan`` is kept verbatim so value validation can reject it by name
    instead of it silently looking like a blank cell.

    Raises ``InvalidInputError`` (naming file and line, with re-export
    guidance) if any data line has a different number of fields than the
    header, e.g. an unquoted ``1,234``.
    """
    if isinstance(source, (str, Path)):
        raw = Path(source).read_bytes()
        source_name = source_name or Path(source).name
    elif isinstance(source, BytesIO):
        raw = source.getvalue()
    else:
        raw = source.read()
    if source_name is None and isinstance(getattr(source, "name", None), str):
        source_name = source.name

    encoding = detect_encoding(raw)
    errors = field_count_errors(raw, encoding, source_name)
    if errors:
        raise InvalidInputError(errors)
    return pd.read_csv(BytesIO(raw), encoding=encoding, keep_default_na=False, na_values=[""])
