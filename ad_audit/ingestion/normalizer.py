"""Column renaming, type coercion, UTM/fbclid extraction, email hashing."""

from __future__ import annotations

from urllib.parse import parse_qs, urlparse

import numpy as np
import pandas as pd

from ad_audit.ingestion.schemas import NUMERIC_RULES, SCHEMAS
from ad_audit.ingestion.validators import (
    InvalidInputError,
    parse_numeric_column,
    raise_if_invalid,
    value_errors,
)
from ad_audit.utils.date_utils import parse_date_column, to_date_only
from ad_audit.utils.hash_utils import hash_email_series


# ---------- Public API ----------

def normalize_meta_ads(df: pd.DataFrame, source_name: str | None = None) -> pd.DataFrame:
    """Rename, parse dates, strictly parse numeric columns, tag platform.

    Raises ``InvalidInputError`` naming file/column/row/value for any invalid
    numeric cell; nothing is coerced to zero.
    """
    df = _strict_numeric(df, "meta_ads", source_name)
    rename = SCHEMAS["meta_ads"].rename
    df = df.rename(columns=rename)

    df["date"] = to_date_only(parse_date_column(df["date"]))

    df["platform"] = "meta"
    return df


def normalize_google_ads(df: pd.DataFrame, source_name: str | None = None) -> pd.DataFrame:
    """Rename, parse dates, strictly parse numeric columns, tag platform.

    Raises ``InvalidInputError`` for any invalid numeric cell.
    """
    df = _strict_numeric(df, "google_ads", source_name)
    rename = SCHEMAS["google_ads"].rename
    df = df.rename(columns=rename)

    df["date"] = to_date_only(parse_date_column(df["date"]))

    # Compute reported_roas from available data
    if "reported_revenue" in df.columns:
        df["reported_roas"] = np.where(
            df["spend"] > 0, df["reported_revenue"] / df["spend"], 0.0
        )
    else:
        df["reported_revenue"] = 0.0
        df["reported_roas"] = 0.0

    df["platform"] = "google_ads"
    return df


def normalize_shopify_orders(df: pd.DataFrame, source_name: str | None = None) -> pd.DataFrame:
    """Rename, parse dates, extract UTM/fbclid, hash emails, collapse multi-lineitem orders.

    ``Total`` is parsed strictly; a blank Total is allowed only on an extra
    row of an order that has a numeric Total elsewhere (it contributes
    nothing to the order sum).  Any other invalid value raises
    ``InvalidInputError``.
    """
    df = _strict_numeric(df, "shopify_orders", source_name)
    rename = SCHEMAS["shopify_orders"].rename
    df = df.rename(columns=rename)

    df["created_at"] = parse_date_column(df["created_at"])
    df["date"] = to_date_only(df["created_at"])

    # UTM & click ID extraction from landing_site
    if "landing_site" in df.columns:
        extracted = df["landing_site"].fillna("").apply(_extract_params)
        df["utm_source"] = extracted.str["utm_source"]
        df["utm_medium"] = extracted.str["utm_medium"]
        df["utm_campaign"] = extracted.str["utm_campaign"]
        df["fbclid"] = extracted.str["fbclid"]
        df["gclid"] = extracted.str["gclid"]

    # Email hashing
    if "email" in df.columns:
        df["email_hash"] = hash_email_series(df["email"])

    # Collapse multi-lineitem orders: keep first row, sum revenue
    if "order_id" in df.columns:
        agg_cols = {c: "first" for c in df.columns if c not in ("order_id", "revenue")}
        agg_cols["revenue"] = "sum"
        df = df.groupby("order_id", as_index=False).agg(agg_cols)

    return df


def normalize_shopify_daily(
    df: pd.DataFrame,
    source_name: str | None = None,
    store_timezone: str | None = None,
) -> pd.DataFrame:
    """Validate and normalize a daily Shopify totals file.

    Input headers are exactly ``date,orders,revenue,currency`` (one row per
    store-local calendar day).  Output columns: ``date`` (datetime64 at
    midnight, no timezone conversion), ``orders`` (int64), ``revenue``
    (float), ``currency`` (str).  A row with orders=0 and revenue=0 is a
    verified zero-order observation.  Duplicate dates, mixed currencies, bad
    dates and invalid numbers raise ``InvalidInputError``; no row is merged,
    added or zero-filled.  *store_timezone* is recorded (not applied) as the
    pilot's stated day-bin timezone.
    """
    raise_if_invalid(df, "shopify_daily", source_name)
    out = pd.DataFrame({
        "date": pd.to_datetime(df["date"].astype(str).str.strip(), format="%Y-%m-%d"),
        "orders": parse_numeric_column(df, "orders", "reject", "shopify_daily", source_name)[0]
        .astype("int64"),
        "revenue": parse_numeric_column(df, "revenue", "reject", "shopify_daily", source_name)[0],
        "currency": df["currency"].astype(str).str.strip(),
    })
    out = out.sort_values("date").reset_index(drop=True)
    out.attrs.update(
        shopify_granularity="daily",
        currency=str(out["currency"].iloc[0]) if len(out) else None,
        store_timezone=store_timezone,
        revenue_definition="gross order Total for orders created that store-local day; refunds not subtracted",
    )
    return out


def normalize_gsc(df: pd.DataFrame, source_name: str | None = None) -> pd.DataFrame:
    """Rename, parse dates, strictly parse clicks/impressions (whole numbers)."""
    df = _strict_numeric(df, "gsc_brand_search", source_name)
    rename = SCHEMAS["gsc_brand_search"].rename
    df = df.rename(columns=rename)

    df["date"] = to_date_only(parse_date_column(df["date"]))

    for col in ("clicks", "impressions"):
        if col in df.columns:
            df[col] = df[col].astype(int)

    return df


def normalize_search_terms(df: pd.DataFrame, source_name: str | None = None) -> pd.DataFrame:
    """Rename and strictly parse search term report columns."""
    df = _strict_numeric(df, "search_terms", source_name)
    rename = SCHEMAS["search_terms"].rename
    df = df.rename(columns=rename)

    # Lowercase search terms for matching
    if "search_term" in df.columns:
        df["search_term_lower"] = df["search_term"].str.lower().str.strip()

    return df


def normalize_user_matched(df: pd.DataFrame, source_name: str | None = None) -> pd.DataFrame:
    """Parse timestamps, strictly parse revenue."""
    df = _strict_numeric(df, "user_matched", source_name)
    df["timestamp"] = parse_date_column(df["timestamp"])
    return df


# ---------- Helpers ----------

def _strict_numeric(df: pd.DataFrame, schema_name: str, source_name: str | None) -> pd.DataFrame:
    """Return a copy of *df* with numeric columns strictly parsed to float.

    Raises ``InvalidInputError`` (file/column/row/value) instead of coercing.
    Blank cells follow the per-column rule in ``schemas.NUMERIC_RULES``.
    """
    errors = value_errors(df, schema_name, source_name)
    if errors:
        raise InvalidInputError(errors)
    df = df.copy()
    for column, rule in NUMERIC_RULES.get(schema_name, {}).items():
        if column in df.columns:
            df[column] = parse_numeric_column(df, column, rule, schema_name, source_name)[0]
    return df


def _extract_params(url: str) -> dict[str, str | None]:
    """Pull UTM params, fbclid, and gclid from a URL/path string."""
    try:
        parsed = urlparse(url if "://" in url else f"https://x.com{url}")
        qs = parse_qs(parsed.query)
        return {
            "utm_source": qs.get("utm_source", [None])[0],
            "utm_medium": qs.get("utm_medium", [None])[0],
            "utm_campaign": qs.get("utm_campaign", [None])[0],
            "fbclid": qs.get("fbclid", [None])[0],
            "gclid": qs.get("gclid", [None])[0],
        }
    except Exception:
        return {"utm_source": None, "utm_medium": None, "utm_campaign": None, "fbclid": None, "gclid": None}
