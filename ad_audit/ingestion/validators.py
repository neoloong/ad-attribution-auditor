"""Schema and value validation for uploaded DataFrames.

Header checks are exact membership tests.  Value checks reject (never coerce)
non-numeric, non-finite and disallowed missing cells in numeric columns, and
enforce the daily Shopify contract (see ``schemas.SHOPIFY_DAILY_REQUIRED``).
Accepted numeric token forms and missing-cell rules are documented in
``schemas`` ("Numeric value rules").  Every error names the file, column,
data row and offending value.
"""

from __future__ import annotations

import datetime as _dt
import math
import re
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from ad_audit.ingestion.schemas import (
    INTEGER_COLUMNS,
    MISSING_MARKERS,
    NUMERIC_KINDS,
    NUMERIC_RULES,
    ROW_LABEL_COLUMNS,
    SCHEMAS,
    SchemaSpec,
)

DEFAULT_SOURCE = "<uploaded file>"

# Plain decimal: optional sign, digits with optional fraction, optional exponent.
_NUMBER_RE = re.compile(r"^[+-]?(\d+(\.\d*)?|\.\d+)([eE][+-]?\d+)?$")
# Strict 3-digit thousands grouping (no leading-zero group), optional fraction.
_GROUPED = r"[1-9]\d{0,2}(?:,\d{3})+(?:\.\d+)?"
_COUNT_RE = re.compile(rf"^(?P<num>{_GROUPED})$")
# Money/ratio: optional "-", one leading currency symbol, plain or grouped
# digits; or the same wrapped in accounting parentheses (no inner sign).
_MONEY_BODY = rf"[$\u00a3\u20ac]?(?P<num>{_GROUPED}|\d+(?:\.\d+)?|\.\d+)"
_MONEY_RE = re.compile(rf"^(?P<neg>-)?{_MONEY_BODY}$")
_MONEY_PAREN_RE = re.compile(rf"^\({_MONEY_BODY}\)$")
_ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_CURRENCY_RE = re.compile(r"^[A-Z]{3}$")


class InvalidInputError(ValueError):
    """Raised when an uploaded file fails value validation."""

    def __init__(self, errors: list[str]):
        self.errors = list(errors)
        shown = self.errors[:20]
        more = len(self.errors) - len(shown)
        message = "\n".join(shown) + (f"\n... and {more} more error(s)" if more > 0 else "")
        super().__init__(message)


@dataclass
class ValidationResult:
    valid: bool
    missing_required: list[str]
    missing_optional: list[str]
    extra_columns: list[str]
    errors: list[str] = field(default_factory=list)
    # Non-fatal findings (e.g. missing cells in unused ratio columns -> NaN).
    warnings: list[str] = field(default_factory=list)


def validate_schema(
    df: pd.DataFrame, schema_name: str, source_name: str | None = None
) -> ValidationResult:
    """Check headers and values of *df* for *schema_name*.

    ``valid`` is False when a required column is missing, when an exact-column
    schema has extra columns, or when any value check fails (``errors``).
    """
    spec: SchemaSpec = SCHEMAS[schema_name]
    source = source_name or DEFAULT_SOURCE
    columns = set(df.columns)

    missing_req = sorted(spec.required - columns)
    missing_opt = sorted(spec.optional - columns)
    known = spec.required | spec.optional
    extra = sorted(columns - known)

    errors: list[str] = []
    if spec.exact_columns and extra:
        errors.append(
            f"{source}: unexpected column(s) {extra}; this file must have exactly the "
            f"columns {sorted(spec.required)}"
        )
    warnings: list[str] = []
    if not missing_req:
        errors.extend(value_errors(df, schema_name, source))
        warnings.extend(value_warnings(df, schema_name, source))

    return ValidationResult(
        valid=len(missing_req) == 0 and not errors,
        missing_required=missing_req,
        missing_optional=missing_opt,
        extra_columns=extra,
        errors=errors,
        warnings=warnings,
    )


def value_errors(df: pd.DataFrame, schema_name: str, source_name: str | None = None) -> list[str]:
    """Return all value-level errors for *df* (raw headers) under *schema_name*."""
    source = source_name or DEFAULT_SOURCE
    errors: list[str] = []
    for column, rule in NUMERIC_RULES.get(schema_name, {}).items():
        if column not in df.columns:
            continue
        _, col_errors = parse_numeric_column(df, column, rule, schema_name, source)
        errors.extend(col_errors)
    if schema_name == "shopify_daily":
        errors.extend(_shopify_daily_errors(df, source))
    return errors


def value_warnings(df: pd.DataFrame, schema_name: str, source_name: str | None = None) -> list[str]:
    """Return non-fatal findings: missing cells kept as NaN in "nan"-rule columns."""
    source = source_name or DEFAULT_SOURCE
    warnings: list[str] = []
    for column, rule in NUMERIC_RULES.get(schema_name, {}).items():
        if rule != "nan" or column not in df.columns:
            continue
        rows = [i for i, cell in enumerate(df[column].tolist())
                if _parse_cell(cell, _kind(schema_name, column))[0] in ("blank", "missing")]
        if rows:
            shown = ", ".join(str(i + 1) for i in rows[:10]) + (" ..." if len(rows) > 10 else "")
            warnings.append(
                f"{source}: column '{column}': {len(rows)} missing cell(s) (data row(s) {shown}) "
                "kept as undefined (NaN); this platform ratio is not used by any engine number"
            )
    return warnings


def parse_numeric_column(
    df: pd.DataFrame, column: str, rule: str, schema_name: str, source_name: str | None = None
) -> tuple[pd.Series, list[str]]:
    """Strictly parse ``df[column]``; return (float Series, errors).

    Accepted token forms depend on the column kind (``schemas.NUMERIC_KINDS``).
    Missing cells (blank, whitespace, or a ``schemas.MISSING_MARKERS`` token)
    become NaN under rule "nan"; under "order_continuation" only a truly
    blank cell on an extra order row is allowed (NaN); otherwise they are
    errors.  Nothing invalid or missing is ever coerced to a number.
    """
    source = source_name or DEFAULT_SOURCE
    kind = _kind(schema_name, column)
    integer = column in INTEGER_COLUMNS.get(schema_name, set())
    values = np.full(len(df), np.nan)
    errors: list[str] = []
    blank_rows: list[int] = []
    marker_rows: list[int] = []
    raw = df[column].tolist()
    for i, cell in enumerate(raw):
        status, number = _parse_cell(cell, kind)
        if status == "blank":
            blank_rows.append(i)
            continue
        if status == "missing":
            marker_rows.append(i)
            continue
        if status == "invalid":
            errors.append(_message(df, i, schema_name, source, column, cell, "is not a valid number"))
            continue
        if not math.isfinite(number):
            errors.append(_message(df, i, schema_name, source, column, cell, "is not finite"))
            continue
        if integer and number != int(number):
            errors.append(_message(df, i, schema_name, source, column, cell, "must be a whole number"))
            continue
        values[i] = number

    if marker_rows and rule != "nan":
        for i in marker_rows:
            errors.append(_message(
                df, i, schema_name, source, column, raw[i],
                "is a missing-value marker; this column needs a number in every row "
                "(write 0 for a real zero; missing values are never read as zero)",
            ))
    if blank_rows:
        if rule == "nan":
            pass
        elif rule == "order_continuation" and "Name" in df.columns:
            names = df["Name"].tolist()
            with_total = {names[i] for i in range(len(df)) if not np.isnan(values[i])}
            for i in blank_rows:
                if names[i] not in with_total or _is_blank(names[i]):
                    errors.append(_message(
                        df, i, schema_name, source, column, raw[i],
                        "is blank and no other row of this order has a numeric Total",
                    ))
        else:
            for i in blank_rows:
                errors.append(_message(df, i, schema_name, source, column, raw[i], "is blank"))
    return pd.Series(values, index=df.index, dtype=float), errors


def raise_if_invalid(df: pd.DataFrame, schema_name: str, source_name: str | None = None) -> None:
    """Raise ``InvalidInputError`` if *df* fails header or value validation."""
    result = validate_schema(df, schema_name, source_name)
    errors = list(result.errors)
    if result.missing_required:
        errors.insert(0, f"{source_name or DEFAULT_SOURCE}: missing required column(s) "
                         f"{result.missing_required}")
    if errors:
        raise InvalidInputError(errors)


# ---------- Shopify daily contract ----------

def _shopify_daily_errors(df: pd.DataFrame, source: str) -> list[str]:
    errors: list[str] = []
    schema = "shopify_daily"

    # date: strict YYYY-MM-DD calendar day, no time or offset, no duplicates.
    parsed: list[_dt.date | None] = []
    for i, cell in enumerate(df["date"].tolist()):
        text = "" if _is_blank(cell) else str(cell).strip()
        day = None
        if _ISO_DATE_RE.match(text):
            try:
                day = _dt.date.fromisoformat(text)
            except ValueError:
                day = None
        if day is None:
            errors.append(_message(df, i, schema, source, "date", cell,
                                   "must be a calendar date in YYYY-MM-DD form"))
        parsed.append(day)
    seen: dict[_dt.date, int] = {}
    for i, day in enumerate(parsed):
        if day is None:
            continue
        if day in seen:
            errors.append(
                f"{source}: column 'date', data row {i + 1}: duplicate date {day.isoformat()} "
                f"(first seen at data row {seen[day] + 1}); one row per day is required, "
                "rows are never merged"
            )
        else:
            seen[day] = i

    # currency: one non-blank ISO 4217-style code for the whole file.
    codes: dict[str, int] = {}
    for i, cell in enumerate(df["currency"].tolist()):
        text = "" if _is_blank(cell) else str(cell).strip()
        if not _CURRENCY_RE.match(text):
            errors.append(_message(df, i, schema, source, "currency", cell,
                                   "must be a 3-letter uppercase ISO 4217 code (e.g. USD)"))
            continue
        codes.setdefault(text, i)
    if len(codes) > 1:
        detail = ", ".join(f"{c} (first at data row {r + 1})" for c, r in codes.items())
        errors.append(
            f"{source}: column 'currency': mixed currencies {detail}; the file must use a "
            "single currency and is never converted"
        )

    # orders/revenue consistency under the adopted revenue definition.
    orders, _ = parse_numeric_column(df, "orders", "reject", schema, source)
    revenue, _ = parse_numeric_column(df, "revenue", "reject", schema, source)
    for i in range(len(df)):
        o, r = orders.iloc[i], revenue.iloc[i]
        if not np.isnan(o) and o < 0:
            errors.append(_message(df, i, schema, source, "orders", df["orders"].iloc[i],
                                   "must be zero or a positive whole number"))
        if not np.isnan(r) and r < 0:
            errors.append(_message(
                df, i, schema, source, "revenue", df["revenue"].iloc[i],
                "is negative; daily revenue must be the gross order Total for orders created "
                "that day (refunds not subtracted), which cannot be negative",
            ))
        if not np.isnan(o) and not np.isnan(r) and o == 0 and r != 0:
            errors.append(_message(
                df, i, schema, source, "revenue", df["revenue"].iloc[i],
                "is non-zero on a day with orders=0; a verified zero-order day must have revenue 0",
            ))
    return errors


# ---------- helpers ----------

def _is_blank(cell) -> bool:
    if cell is None:
        return True
    if isinstance(cell, float) and math.isnan(cell):
        return True
    if cell is pd.NA or cell is pd.NaT:
        return True
    return isinstance(cell, str) and cell.strip() == ""


def _kind(schema_name: str, column: str) -> str:
    return NUMERIC_KINDS.get(schema_name, {}).get(column, "plain")


def _parse_cell(cell, kind: str = "plain") -> tuple[str, float]:
    """Return ("blank"|"missing"|"invalid"|"ok", value).

    "blank" = empty/whitespace; "missing" = a ``MISSING_MARKERS`` token.
    Plain decimals parse exactly as before for every kind; the extra forms
    are allowed only for "count" (thousands grouping) and "money"/"ratio"
    (grouping, one leading currency symbol, accounting parentheses).
    """
    if _is_blank(cell):
        return "blank", math.nan
    if isinstance(cell, (bool, np.bool_)):
        return "invalid", math.nan
    if isinstance(cell, (int, float, np.integer, np.floating)):
        return "ok", float(cell)
    text = str(cell).strip()
    if _NUMBER_RE.match(text):
        return "ok", float(text)
    if text in MISSING_MARKERS:
        return "missing", math.nan
    if kind == "count":
        m = _COUNT_RE.match(text)
        if m:
            return "ok", float(m.group("num").replace(",", ""))
    elif kind in ("money", "ratio"):
        m = _MONEY_RE.match(text)
        negative = bool(m and m.group("neg"))
        if not m:
            m = _MONEY_PAREN_RE.match(text)
            negative = bool(m)
        if m:
            number = float(m.group("num").replace(",", ""))
            return "ok", -number if negative else number
    return "invalid", math.nan


def _message(df, i, schema_name, source, column, cell, problem) -> str:
    labels = []
    for label_col in ROW_LABEL_COLUMNS.get(schema_name, ()):
        if label_col in df.columns and label_col != column:
            labels.append(f"{label_col}={df[label_col].iloc[i]!r}")
    where = f"data row {i + 1}" + (f" ({', '.join(labels)})" if labels else "")
    shown = "<blank>" if _is_blank(cell) else repr(cell)
    return f"{source}: column '{column}', {where}: value {shown} {problem}"
