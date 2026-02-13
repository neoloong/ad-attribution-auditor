"""Tests for search term wasted spend analysis."""

import pandas as pd
import numpy as np

from ad_audit.engine.search_term_analysis import (
    analyze_search_terms,
    SearchTermAnalysisResult,
)


def _make_search_terms_df():
    return pd.DataFrame({
        "search_term": ["mybrand shoes", "running shoes", "cheap sneakers", "mybrand"],
        "search_term_lower": ["mybrand shoes", "running shoes", "cheap sneakers", "mybrand"],
        "campaign_name": ["Brand", "Non-Brand", "Non-Brand", "Brand"],
        "spend": [50.0, 120.0, 80.0, 30.0],
        "reported_conversions": [5.0, 2.0, 0.0, 3.0],
        "clicks": [30, 60, 40, 20],
        "impressions": [300, 800, 500, 200],
        "reported_revenue": [400.0, 160.0, 0.0, 240.0],
    })


def _make_shopify_df():
    rng = np.random.default_rng(42)
    return pd.DataFrame({
        "order_id": [f"#10{i:02d}" for i in range(20)],
        "date": pd.date_range("2024-01-01", periods=20, freq="D"),
        "revenue": rng.uniform(30, 100, size=20).round(2),
        "utm_source": ["google"] * 10 + ["facebook"] * 5 + [""] * 5,
        "utm_medium": ["cpc"] * 10 + ["paid"] * 5 + [""] * 5,
        "gclid": [f"gc{i}" if i < 10 else "" for i in range(20)],
        "fbclid": [""] * 10 + [f"fb{i}" for i in range(5)] + [""] * 5,
    })


def test_basic_analysis():
    st_df = _make_search_terms_df()
    shopify_df = _make_shopify_df()
    result = analyze_search_terms(st_df, shopify_df)

    assert isinstance(result, SearchTermAnalysisResult)
    assert result.total_terms == 4
    assert result.total_spend > 0
    assert result.wasted_spend >= 0
    assert 0 <= result.wasted_spend_pct <= 1
    assert result.summary_df is not None
    assert len(result.summary_df) == 4


def test_brand_term_detection():
    st_df = _make_search_terms_df()
    shopify_df = _make_shopify_df()
    result = analyze_search_terms(st_df, shopify_df, brand_terms=["mybrand"])

    assert result.brand_term_spend > 0
    brand_insights = [i for i in result.insights if i.is_brand_term]
    assert len(brand_insights) == 2  # "mybrand shoes" and "mybrand"


def test_empty_search_terms():
    st_df = pd.DataFrame()
    shopify_df = _make_shopify_df()
    result = analyze_search_terms(st_df, shopify_df)

    assert result.total_terms == 0
    assert result.total_spend == 0
    assert result.wasted_spend == 0


def test_empty_shopify():
    st_df = _make_search_terms_df()
    shopify_df = pd.DataFrame({
        "order_id": pd.Series(dtype="str"),
        "date": pd.Series(dtype="datetime64[ns]"),
        "revenue": pd.Series(dtype="float"),
        "utm_medium": pd.Series(dtype="str"),
    })
    result = analyze_search_terms(st_df, shopify_df)

    # All spend is "wasted" since no verified orders
    assert result.total_terms == 4
    assert result.wasted_spend == result.total_spend


def test_insights_sorted_by_wasted_spend():
    st_df = _make_search_terms_df()
    shopify_df = _make_shopify_df()
    result = analyze_search_terms(st_df, shopify_df)

    wasted = [i.wasted_spend for i in result.insights]
    assert wasted == sorted(wasted, reverse=True)
