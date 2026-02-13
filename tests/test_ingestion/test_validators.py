"""Tests for schema validation."""

import pandas as pd

from ad_audit.ingestion.validators import validate_schema


def test_valid_meta_ads():
    df = pd.DataFrame({
        "Day": ["2024-01-01"],
        "Campaign name": ["Test"],
        "Amount spent (USD)": [100.0],
        "Purchases": [5],
        "Purchase conversion value": [500.0],
        "Purchase ROAS": [5.0],
    })
    result = validate_schema(df, "meta_ads")
    assert result.valid
    assert result.missing_required == []


def test_missing_required_column():
    df = pd.DataFrame({
        "Day": ["2024-01-01"],
        # Missing "Campaign name"
        "Amount spent (USD)": [100.0],
        "Purchases": [5],
    })
    result = validate_schema(df, "meta_ads")
    assert not result.valid
    assert "Campaign name" in result.missing_required


def test_valid_shopify():
    df = pd.DataFrame({
        "Name": ["#1001"],
        "Email": ["a@b.com"],
        "Created at": ["2024-01-01"],
        "Total": [50.0],
    })
    result = validate_schema(df, "shopify_orders")
    assert result.valid


def test_valid_google_ads():
    df = pd.DataFrame({
        "Day": ["2024-01-01"],
        "Campaign": ["Search - Brand"],
        "Cost": [80.0],
        "Conversions": [4],
        "Conv. value": [320.0],
        "Cost / conv.": [20.0],
    })
    result = validate_schema(df, "google_ads")
    assert result.valid
    assert result.missing_required == []


def test_valid_search_terms():
    df = pd.DataFrame({
        "Search term": ["mybrand shoes"],
        "Campaign": ["Brand"],
        "Cost": [50.0],
        "Conversions": [5],
        "Impressions": [300],
        "Clicks": [30],
        "Conv. value": [400.0],
        "Ad group": ["Auto"],
    })
    result = validate_schema(df, "search_terms")
    assert result.valid
    assert result.missing_required == []


def test_valid_gsc():
    df = pd.DataFrame({
        "Date": ["2024-01-01"],
        "Top queries": ["brand"],
        "Clicks": [10],
    })
    result = validate_schema(df, "gsc_brand_search")
    assert result.valid
