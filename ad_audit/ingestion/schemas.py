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


@dataclass
class SchemaSpec:
    required: set[str]
    optional: set[str]
    rename: dict[str, str]


SCHEMAS: dict[str, SchemaSpec] = {
    "meta_ads": SchemaSpec(META_ADS_REQUIRED, META_ADS_OPTIONAL, META_ADS_RENAME),
    "google_ads": SchemaSpec(GOOGLE_ADS_REQUIRED, GOOGLE_ADS_OPTIONAL, GOOGLE_ADS_RENAME),
    "shopify_orders": SchemaSpec(SHOPIFY_REQUIRED, SHOPIFY_OPTIONAL, SHOPIFY_RENAME),
    "gsc_brand_search": SchemaSpec(GSC_REQUIRED, GSC_OPTIONAL, GSC_RENAME),
    "search_terms": SchemaSpec(SEARCH_TERMS_REQUIRED, SEARCH_TERMS_OPTIONAL, SEARCH_TERMS_RENAME),
    "user_matched": SchemaSpec(USER_MATCHED_REQUIRED, USER_MATCHED_OPTIONAL, {}),
}
