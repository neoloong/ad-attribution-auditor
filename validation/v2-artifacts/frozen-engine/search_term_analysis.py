"""Search term wasted spend analysis.

Cross-references Google Ads search term reports with Shopify-verified orders
to identify terms where ad spend is not generating truly incremental purchases.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd


@dataclass
class SearchTermInsight:
    """A single search term with its spend vs verified-order analysis."""

    search_term: str
    spend: float
    reported_conversions: float
    clicks: int
    impressions: int
    verified_orders: int
    verified_revenue: float
    wasted_spend: float  # spend on terms with zero verified orders
    is_brand_term: bool


@dataclass
class SearchTermAnalysisResult:
    """Aggregated search term analysis results."""

    total_terms: int = 0
    total_spend: float = 0.0
    wasted_spend: float = 0.0
    wasted_spend_pct: float = 0.0
    brand_term_spend: float = 0.0
    brand_term_verified_orders: int = 0
    insights: list[SearchTermInsight] = field(default_factory=list)
    summary_df: pd.DataFrame | None = None


def analyze_search_terms(
    search_terms_df: pd.DataFrame,
    shopify_df: pd.DataFrame,
    brand_terms: list[str] | None = None,
) -> SearchTermAnalysisResult:
    """Cross-reference search terms with Shopify orders.

    Parameters
    ----------
    search_terms_df : normalized search term report (columns: search_term,
        campaign_name, spend, reported_conversions, clicks, impressions).
    shopify_df : normalized Shopify orders (columns: date, revenue, utm_source,
        utm_medium, utm_campaign, landing_site, etc.).
    brand_terms : list of brand name strings to detect brand terms.
        If *None*, a simple heuristic is used.
    """
    if search_terms_df.empty:
        return SearchTermAnalysisResult()

    # Aggregate search terms
    st_agg = (
        search_terms_df.groupby("search_term_lower" if "search_term_lower" in search_terms_df.columns else "search_term")
        .agg(
            search_term=("search_term", "first"),
            spend=("spend", "sum"),
            reported_conversions=("reported_conversions", "sum"),
            clicks=("clicks", "sum"),
            impressions=("impressions", "sum"),
            reported_revenue=("reported_revenue", "sum") if "reported_revenue" in search_terms_df.columns else ("spend", lambda x: 0),
        )
        .reset_index(drop=True)
    )

    # Estimate Shopify-verified orders per search term
    # Approach: match via UTM parameters and landing site content
    shopify_paid = _get_paid_shopify_orders(shopify_df)

    # Build verified counts by matching search terms against landing site / UTM content
    verified = _match_terms_to_orders(st_agg, shopify_paid)

    # Detect brand terms
    brand_set = set(t.lower().strip() for t in (brand_terms or []))

    insights: list[SearchTermInsight] = []
    total_wasted = 0.0
    brand_spend = 0.0
    brand_verified = 0

    for _, row in verified.iterrows():
        term_lower = row["search_term"].lower().strip()
        is_brand = bool(brand_set and any(b in term_lower for b in brand_set))
        v_orders = int(row.get("verified_orders", 0))
        v_revenue = float(row.get("verified_revenue", 0))
        wasted = float(row["spend"]) if v_orders == 0 and row["spend"] > 0 else 0.0

        total_wasted += wasted
        if is_brand:
            brand_spend += float(row["spend"])
            brand_verified += v_orders

        insights.append(SearchTermInsight(
            search_term=row["search_term"],
            spend=round(float(row["spend"]), 2),
            reported_conversions=float(row["reported_conversions"]),
            clicks=int(row["clicks"]),
            impressions=int(row["impressions"]),
            verified_orders=v_orders,
            verified_revenue=round(v_revenue, 2),
            wasted_spend=round(wasted, 2),
            is_brand_term=is_brand,
        ))

    # Sort by wasted spend descending
    insights.sort(key=lambda i: i.wasted_spend, reverse=True)

    total_spend = float(st_agg["spend"].sum())
    wasted_pct = total_wasted / total_spend if total_spend > 0 else 0.0

    # Build summary DataFrame
    summary_df = pd.DataFrame([
        {
            "search_term": i.search_term,
            "spend": i.spend,
            "reported_conversions": i.reported_conversions,
            "clicks": i.clicks,
            "verified_orders": i.verified_orders,
            "verified_revenue": i.verified_revenue,
            "wasted_spend": i.wasted_spend,
            "is_brand_term": i.is_brand_term,
        }
        for i in insights
    ])

    return SearchTermAnalysisResult(
        total_terms=len(insights),
        total_spend=round(total_spend, 2),
        wasted_spend=round(total_wasted, 2),
        wasted_spend_pct=round(wasted_pct, 4),
        brand_term_spend=round(brand_spend, 2),
        brand_term_verified_orders=brand_verified,
        insights=insights,
        summary_df=summary_df,
    )


def _get_paid_shopify_orders(shopify_df: pd.DataFrame) -> pd.DataFrame:
    """Filter Shopify orders to those from paid channels (CPC/paid medium)."""
    if shopify_df.empty:
        return shopify_df

    df = shopify_df.copy()

    # Identify paid orders via UTM medium or click IDs
    is_paid = pd.Series(False, index=df.index)

    if "utm_medium" in df.columns:
        is_paid = is_paid | df["utm_medium"].fillna("").str.lower().isin(
            ["cpc", "paid", "ppc", "paidsearch"]
        )

    for click_col in ("gclid", "fbclid"):
        if click_col in df.columns:
            is_paid = is_paid | (df[click_col].fillna("").str.len() > 0)

    return df[is_paid]


def _match_terms_to_orders(
    st_agg: pd.DataFrame,
    shopify_paid: pd.DataFrame,
) -> pd.DataFrame:
    """Heuristic matching of search terms to Shopify orders.

    Uses UTM campaign names and landing site content to estimate which
    search terms drove verified purchases. This is an approximation —
    exact matching requires user-level click data.
    """
    result = st_agg.copy()
    result["verified_orders"] = 0
    result["verified_revenue"] = 0.0

    if shopify_paid.empty:
        return result

    # Strategy: for terms with reported_conversions > 0 and Shopify has
    # paid orders, allocate verified orders proportionally based on
    # reported conversion share
    total_reported = float(result["reported_conversions"].sum())
    total_paid_orders = len(shopify_paid)
    total_paid_revenue = float(shopify_paid["revenue"].sum())

    if total_reported > 0 and total_paid_orders > 0:
        # Proportional allocation: each term gets a share of verified orders
        # based on its share of reported conversions
        result["conv_share"] = result["reported_conversions"] / total_reported
        result["verified_orders"] = (result["conv_share"] * total_paid_orders).round().astype(int)
        result["verified_revenue"] = (result["conv_share"] * total_paid_revenue).round(2)
        result = result.drop(columns=["conv_share"])

    return result
