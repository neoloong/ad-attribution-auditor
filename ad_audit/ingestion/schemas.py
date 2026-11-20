"""Column schemas for each supported CSV type."""

from __future__ import annotations

from dataclasses import dataclass

# ---------- Meta Ads ----------
META_ADS_REQUIRED = {
    "Day",
    "Campaign name",
    "Amount spent (USD)",
    "Purchases",
}
META_ADS_OPTIONAL = {
    "Purchase conversion value",
    "Purchase ROAS",
}
META_ADS_RENAME = {
    "Day": "date",
    "Campaign name": "campaign_name",
    "Amount spent (USD)": "spend",
    "Purchases": "reported_conversions",
    "Purchase conversion value": "reported_revenue",
    "Purchase ROAS": "reported_roas",
}

# ---------- Google Ads ----------
GOOGLE_ADS_REQUIRED = {
    "Day",
    "Campaign",
    "Cost",
    "Conversions",
}
GOOGLE_ADS_OPTIONAL = {
    "Conv. value",
    "Cost / conv.",
}
GOOGLE_ADS_RENAME = {
    "Day": "date",
    "Campaign": "campaign_name",
    "Cost": "spend",
    "Conversions": "reported_conversions",
    "Conv. value": "reported_revenue",
    "Cost / conv.": "cost_per_conversion",
}

# ---------- Shopify Orders ----------
SHOPIFY_REQUIRED = {
    "Name",
    "Email",
    "Created at",
    "Total",
}
SHOPIFY_OPTIONAL = {
    "Referring Site",
    "Landing Site",
}
SHOPIFY_RENAME = {
    "Name": "order_id",
    "Email": "email",
    "Created at": "created_at",
    "Total": "revenue",
    "Referring Site": "referring_site",
    "Landing Site": "landing_site",
}

# ---------- Shopify Daily Totals (one row per store-local calendar day) ----------
# Exact headers, nothing else. ``orders`` is the integer count of orders
# created that day (0 is a real observation), ``revenue`` is the gross sum of
# order ``Total`` for those orders (same definition as the order-level path;
# refunds are NOT subtracted), ``currency`` is one ISO 4217 code for the file.
SHOPIFY_DAILY_REQUIRED = {
    "date",
    "orders",
    "revenue",
    "currency",
}
SHOPIFY_DAILY_OPTIONAL: set[str] = set()
SHOPIFY_DAILY_RENAME: dict[str, str] = {}

# ---------- Google Search Console ----------
GSC_REQUIRED = {
    "Date",
    "Top queries",
    "Clicks",
}
GSC_OPTIONAL = {
    "Impressions",
}
GSC_RENAME = {
    "Date": "date",
    "Top queries": "query",
    "Clicks": "clicks",
    "Impressions": "impressions",
}

# ---------- Google Ads Search Terms ----------
SEARCH_TERMS_REQUIRED = {
    "Search term",
    "Campaign",
    "Cost",
    "Conversions",
    "Impressions",
    "Clicks",
}
SEARCH_TERMS_OPTIONAL = {
    "Conv. value",
    "Ad group",
}
SEARCH_TERMS_RENAME = {
    "Search term": "search_term",
    "Campaign": "campaign_name",
    "Cost": "spend",
    "Conversions": "reported_conversions",
    "Impressions": "impressions",
    "Clicks": "clicks",
    "Conv. value": "reported_revenue",
    "Ad group": "ad_group",
}

# ---------- User-Matched Events ----------
USER_MATCHED_REQUIRED = {
    "user_id",
    "email_hash",
    "event_type",
    "event_source",
    "timestamp",
    "revenue",
}
USER_MATCHED_OPTIONAL = {
    "fbclid",
    "gclid",
}


# ---------- Numeric value rules ----------
# Every numeric column is parsed strictly and must be finite, otherwise the
# file is rejected.  Accepted token forms depend on the column KIND
# (``NUMERIC_KINDS``):
#   plain   (all kinds)  decimal number, optional sign/exponent: 12, -3.5, 1e3
#   "count"              plus strict 3-digit thousands grouping: 1,234 / 1,234.5
#                        (the field must be quoted in the CSV)
#   "money" / "ratio"    plus thousands grouping, ONE leading currency symbol
#                        ($ £ €; also -$5) and accounting negatives:
#                        (123.45) / ($1,234.50) -> -123.45 / -1234.5
# Never accepted: "nan", "inf", "abc", 12.3.4, 1,2,3, 12,34, European
# 1.234,56, trailing/ISO currency (12.50 €, USD 12), 1_000, TRUE.
#
# A MISSING cell is blank, whitespace-only, or a missing marker
# (``MISSING_MARKERS``: --  -  —  –  n/a  N/A).  What happens to it is the
# per-column rule in ``NUMERIC_RULES``; nothing is ever read as zero:
#   "reject"       missing cell rejects the file (every money and count
#                  column, including the optional platform-claimed
#                  conversion-value columns, which feed reported revenue,
#                  reported ROAS and the inflation rate)
#   "nan"          missing cell = undefined ratio, kept as NaN and reported
#                  as a validation WARNING; only for OPTIONAL
#                  platform-computed ratio columns that no engine number reads
#   "order_continuation"
#                  Shopify order-level ``Total``: a BLANK (empty/whitespace)
#                  cell is allowed only on an extra row of an order (same
#                  ``Name``) that has a numeric ``Total`` on another row; an
#                  order with no numeric Total, or a missing marker such as
#                  "--", rejects the file
MISSING_MARKERS = frozenset({"--", "-", "\u2014", "\u2013", "n/a", "N/A"})

NUMERIC_RULES: dict[str, dict[str, str]] = {
    "meta_ads": {
        "Amount spent (USD)": "reject",
        "Purchases": "reject",
        "Purchase conversion value": "reject",
        "Purchase ROAS": "nan",
    },
    "google_ads": {
        "Cost": "reject",
        "Conversions": "reject",
        "Conv. value": "reject",
        "Cost / conv.": "nan",
    },
    "shopify_orders": {"Total": "order_continuation"},
    "shopify_daily": {"orders": "reject", "revenue": "reject"},
    "gsc_brand_search": {"Clicks": "reject", "Impressions": "reject"},
    "search_terms": {
        "Cost": "reject",
        "Conversions": "reject",
        "Impressions": "reject",
        "Clicks": "reject",
        "Conv. value": "reject",
    },
    "user_matched": {"revenue": "reject"},
}

# Token grammar per numeric column (see above).
NUMERIC_KINDS: dict[str, dict[str, str]] = {
    "meta_ads": {
        "Amount spent (USD)": "money",
        "Purchases": "count",
        "Purchase conversion value": "money",
        "Purchase ROAS": "ratio",
    },
    "google_ads": {
        "Cost": "money",
        "Conversions": "count",
        "Conv. value": "money",
        "Cost / conv.": "ratio",
    },
    "shopify_orders": {"Total": "money"},
    "shopify_daily": {"orders": "count", "revenue": "money"},
    "gsc_brand_search": {"Clicks": "count", "Impressions": "count"},
    "search_terms": {
        "Cost": "money",
        "Conversions": "count",
        "Impressions": "count",
        "Clicks": "count",
        "Conv. value": "money",
    },
    "user_matched": {"revenue": "money"},
}

# Columns whose values must be whole numbers.
INTEGER_COLUMNS: dict[str, set[str]] = {
    "shopify_daily": {"orders"},
    "gsc_brand_search": {"Clicks", "Impressions"},
}

# Column used to identify a row in error messages (raw header names).
ROW_LABEL_COLUMNS: dict[str, tuple[str, ...]] = {
    "meta_ads": ("Day", "Campaign name"),
    "google_ads": ("Day", "Campaign"),
    "shopify_orders": ("Name", "Created at"),
    "shopify_daily": ("date",),
    "gsc_brand_search": ("Date",),
    "search_terms": ("Search term", "Campaign"),
    "user_matched": ("user_id", "timestamp"),
}


@dataclass
class SchemaSpec:
    required: set[str]
    optional: set[str]
    rename: dict[str, str]
    # When True, columns outside required|optional reject the file.
    exact_columns: bool = False


SCHEMAS: dict[str, SchemaSpec] = {
    "meta_ads": SchemaSpec(META_ADS_REQUIRED, META_ADS_OPTIONAL, META_ADS_RENAME),
    "google_ads": SchemaSpec(GOOGLE_ADS_REQUIRED, GOOGLE_ADS_OPTIONAL, GOOGLE_ADS_RENAME),
    "shopify_orders": SchemaSpec(SHOPIFY_REQUIRED, SHOPIFY_OPTIONAL, SHOPIFY_RENAME),
    "shopify_daily": SchemaSpec(
        SHOPIFY_DAILY_REQUIRED, SHOPIFY_DAILY_OPTIONAL, SHOPIFY_DAILY_RENAME, exact_columns=True,
    ),
    "gsc_brand_search": SchemaSpec(GSC_REQUIRED, GSC_OPTIONAL, GSC_RENAME),
    "search_terms": SchemaSpec(SEARCH_TERMS_REQUIRED, SEARCH_TERMS_OPTIONAL, SEARCH_TERMS_RENAME),
    "user_matched": SchemaSpec(USER_MATCHED_REQUIRED, USER_MATCHED_OPTIONAL, {}),
}
