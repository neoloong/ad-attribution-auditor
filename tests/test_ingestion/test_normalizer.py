"""Tests for normalizer."""

import pandas as pd
import numpy as np

from ad_audit.ingestion.normalizer import (
    normalize_meta_ads,
    normalize_google_ads,
    normalize_shopify_orders,
    normalize_gsc,
    normalize_search_terms,
    normalize_user_matched,
    _extract_params,
)


def test_normalize_meta_ads():
    df = pd.DataFrame({
        "Day": ["2024-01-01", "2024-01-02"],
        "Campaign name": ["C1", "C1"],
        "Amount spent (USD)": ["100.5", "0"],
        "Purchases": ["5", "0"],
        "Purchase conversion value": ["500", "0"],
        "Purchase ROAS": ["5.0", "0"],
    })
    result = normalize_meta_ads(df)
    assert "date" in result.columns
    assert "spend" in result.columns
    assert result["spend"].dtype == float
    assert result["date"].dtype == "datetime64[ns]"
    assert (result["platform"] == "meta").all()


def test_normalize_google_ads():
    df = pd.DataFrame({
        "Day": ["2024-01-01", "2024-01-02"],
        "Campaign": ["Search - Brand", "Search - Brand"],
        "Cost": ["80.0", "0"],
        "Conversions": ["4", "0"],
        "Conv. value": ["320", "0"],
        "Cost / conv.": ["20.0", "0"],
    })
    result = normalize_google_ads(df)
    assert "date" in result.columns
    assert "spend" in result.columns
    assert "reported_conversions" in result.columns
    assert "reported_revenue" in result.columns
    assert "reported_roas" in result.columns
    assert result["spend"].dtype == float
    assert result["date"].dtype == "datetime64[ns]"
    assert (result["platform"] == "google_ads").all()
    assert result.loc[0, "reported_roas"] == 320.0 / 80.0


def test_normalize_shopify_orders():
    df = pd.DataFrame({
        "Name": ["#1001", "#1001", "#1002"],
        "Email": ["a@b.com", "a@b.com", "c@d.com"],
        "Created at": ["2024-01-01 10:00:00", "2024-01-01 10:00:00", "2024-01-02"],
        "Total": [50.0, 25.0, 80.0],
        "Referring Site": ["https://facebook.com", "https://facebook.com", ""],
        "Landing Site": [
            "/test?utm_source=facebook&fbclid=abc123",
            "/test?utm_source=facebook&fbclid=abc123",
            "/test",
        ],
    })
    result = normalize_shopify_orders(df)
    # Multi-lineitem #1001 should be collapsed
    assert len(result) == 2
    order_1001 = result[result["order_id"] == "#1001"]
    assert order_1001["revenue"].iloc[0] == 75.0
    assert "email_hash" in result.columns
    assert "fbclid" in result.columns
    assert "utm_source" in result.columns


def test_normalize_gsc():
    df = pd.DataFrame({
        "Date": ["2024-01-01"],
        "Top queries": ["mybrand"],
        "Clicks": ["10"],
        "Impressions": ["100"],
    })
    result = normalize_gsc(df)
    assert result["clicks"].dtype in (int, np.int64)
    assert "date" in result.columns


def test_normalize_search_terms():
    df = pd.DataFrame({
        "Search term": ["mybrand shoes", "running shoes"],
        "Campaign": ["Brand", "Non-Brand"],
        "Cost": ["50.0", "120.0"],
        "Conversions": ["5", "2"],
        "Impressions": ["300", "800"],
        "Clicks": ["30", "60"],
        "Conv. value": ["400", "160"],
        "Ad group": ["Auto", "Broad"],
    })
    result = normalize_search_terms(df)
    assert "search_term" in result.columns
    assert "spend" in result.columns
    assert "search_term_lower" in result.columns
    assert result["spend"].dtype == float
    assert result.loc[0, "search_term_lower"] == "mybrand shoes"


def test_normalize_user_matched():
    df = pd.DataFrame({
        "user_id": ["u1"],
        "email_hash": ["abc"],
        "event_type": ["purchase"],
        "event_source": ["shopify"],
        "timestamp": ["2024-01-01T10:00:00"],
        "revenue": ["50.0"],
        "fbclid": ["fb1"],
    })
    result = normalize_user_matched(df)
    assert result["revenue"].dtype == float


def test_extract_params():
    result = _extract_params("/products?utm_source=facebook&utm_medium=paid&fbclid=abc")
    assert result["utm_source"] == "facebook"
    assert result["utm_medium"] == "paid"
    assert result["fbclid"] == "abc"


def test_extract_params_with_gclid():
    result = _extract_params("/products?utm_source=google&utm_medium=cpc&gclid=abc123")
    assert result["utm_source"] == "google"
    assert result["utm_medium"] == "cpc"
    assert result["gclid"] == "abc123"
    assert result["fbclid"] is None


def test_extract_params_empty():
    result = _extract_params("")
    assert result["utm_source"] is None
    assert result["gclid"] is None
