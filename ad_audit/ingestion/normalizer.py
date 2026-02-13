"""Column renaming, type coercion, UTM/fbclid extraction, email hashing."""

from __future__ import annotations

from urllib.parse import parse_qs, urlparse

import numpy as np
import pandas as pd

from ad_audit.ingestion.schemas import SCHEMAS
from ad_audit.utils.date_utils import parse_date_column, to_date_only
from ad_audit.utils.hash_utils import hash_email_series


# ---------- Public API ----------

def normalize_meta_ads(df: pd.DataFrame) -> pd.DataFrame:
    """Rename, parse dates, coerce numeric columns, tag platform."""
    df = df.copy()
    rename = SCHEMAS["meta_ads"].rename
    df = df.rename(columns=rename)

    df["date"] = to_date_only(parse_date_column(df["date"]))

    for col in ("spend", "reported_conversions", "reported_revenue", "reported_roas"):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    df["platform"] = "meta"
    return df


def normalize_google_ads(df: pd.DataFrame) -> pd.DataFrame:
    """Rename, parse dates, coerce numeric columns, tag platform."""
    df = df.copy()
    rename = SCHEMAS["google_ads"].rename
    df = df.rename(columns=rename)

    df["date"] = to_date_only(parse_date_column(df["date"]))

    for col in ("spend", "reported_conversions", "reported_revenue", "cost_per_conversion"):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

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


def normalize_shopify_orders(df: pd.DataFrame) -> pd.DataFrame:
    """Rename, parse dates, extract UTM/fbclid, hash emails, collapse multi-lineitem orders."""
    df = df.copy()
    rename = SCHEMAS["shopify_orders"].rename
    df = df.rename(columns=rename)

    df["created_at"] = parse_date_column(df["created_at"])
    df["date"] = to_date_only(df["created_at"])
    df["revenue"] = pd.to_numeric(df["revenue"], errors="coerce").fillna(0)

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


def normalize_gsc(df: pd.DataFrame) -> pd.DataFrame:
    """Rename, parse dates, coerce clicks/impressions."""
    df = df.copy()
    rename = SCHEMAS["gsc_brand_search"].rename
    df = df.rename(columns=rename)

    df["date"] = to_date_only(parse_date_column(df["date"]))

    for col in ("clicks", "impressions"):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)

    return df


def normalize_search_terms(df: pd.DataFrame) -> pd.DataFrame:
    """Rename and coerce search term report columns."""
    df = df.copy()
    rename = SCHEMAS["search_terms"].rename
    df = df.rename(columns=rename)

    for col in ("spend", "reported_conversions", "clicks", "impressions", "reported_revenue"):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    # Lowercase search terms for matching
    if "search_term" in df.columns:
        df["search_term_lower"] = df["search_term"].str.lower().str.strip()

    return df


def normalize_user_matched(df: pd.DataFrame) -> pd.DataFrame:
    """Parse timestamps, coerce revenue."""
    df = df.copy()
    df["timestamp"] = parse_date_column(df["timestamp"])
    df["revenue"] = pd.to_numeric(df["revenue"], errors="coerce").fillna(0)
    return df


# ---------- Helpers ----------

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
