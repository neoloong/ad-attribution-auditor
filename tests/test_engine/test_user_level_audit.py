"""Tests for user-level audit engine."""

import pandas as pd

from ad_audit.engine.user_level_audit import (
    run_user_level_audit,
    _match_purchases_to_clicks,
    _check_brand_search_overlap,
)
from ad_audit.engine.models import AuditConfig, AuditMode


def test_match_purchases_to_clicks():
    clicks = pd.DataFrame({
        "user_id": ["u1", "u2"],
        "email_hash": ["h1", "h2"],
        "timestamp": pd.to_datetime(["2024-01-01 10:00", "2024-01-01 12:00"]),
        "fbclid": ["fb1", "fb2"],
    })
    purchases = pd.DataFrame({
        "user_id": ["u1", "u2", "u3"],
        "email_hash": ["h1", "h2", "h3"],
        "timestamp": pd.to_datetime(["2024-01-03", "2024-01-02", "2024-01-05"]),
        "revenue": [100, 50, 80],
        "fbclid": ["fb1", None, None],
    })
    config = AuditConfig(attribution_window_days=7)
    matched = _match_purchases_to_clicks(clicks, purchases, config)
    # u1 and u2 should match; u3 has no click
    assert len(matched) == 2
    assert set(matched["user_id"]) == {"u1", "u2"}


def test_brand_search_overlap():
    matched = pd.DataFrame({
        "user_id": ["u1", "u2"],
        "email_hash": ["h1", "h2"],
        "click_time": pd.to_datetime(["2024-01-01 10:00", "2024-01-01 12:00"]),
        "timestamp": pd.to_datetime(["2024-01-03", "2024-01-03"]),
        "revenue": [100, 50],
    })
    brand_searches = pd.DataFrame({
        "email_hash": ["h1"],
        "timestamp": pd.to_datetime(["2024-01-01 05:00"]),
    })
    config = AuditConfig(cannibalization_lookback_hours=24)
    result = _check_brand_search_overlap(matched, brand_searches, config)
    assert result.loc[result["user_id"] == "u1", "is_cannibalized"].iloc[0] == True
    assert result.loc[result["user_id"] == "u2", "is_cannibalized"].iloc[0] == False


def test_run_user_level_audit(sample_user_matched_df):
    config = AuditConfig(mode=AuditMode.USER_LEVEL)
    result = run_user_level_audit(sample_user_matched_df, config)
    assert result.mode == AuditMode.USER_LEVEL
    assert result.total_matched_orders > 0
    assert result.cannibalized_orders >= 0
    assert result.truly_incremental_orders >= 0
    assert result.truly_incremental_orders + result.cannibalized_orders == result.total_matched_orders


def test_run_user_level_audit_no_brand_search():
    events = pd.DataFrame({
        "user_id": ["u1", "u1"],
        "email_hash": ["h1", "h1"],
        "event_type": ["ad_click", "purchase"],
        "event_source": ["meta", "shopify"],
        "timestamp": pd.to_datetime(["2024-01-01 10:00", "2024-01-03 10:00"]),
        "revenue": [0, 100],
        "fbclid": ["fb1", "fb1"],
        "gclid": ["", ""],
    })
    result = run_user_level_audit(events)
    assert result.total_matched_orders == 1
    assert result.cannibalized_orders == 0


def test_gclid_matching():
    """User-level audit matches purchases via gclid (Google Ads click ID)."""
    events = pd.DataFrame({
        "user_id": ["u1", "u1", "u2", "u2"],
        "email_hash": ["h1", "h1", "h2", "h2"],
        "event_type": ["ad_click", "purchase", "ad_click", "purchase"],
        "event_source": ["google_ads", "shopify", "google_ads", "shopify"],
        "timestamp": pd.to_datetime([
            "2024-01-01 10:00", "2024-01-03 10:00",
            "2024-01-02 10:00", "2024-01-04 10:00",
        ]),
        "revenue": [0, 100, 0, 80],
        "fbclid": ["", "", "", ""],
        "gclid": ["gc1", "gc1", "gc2", ""],
    })
    result = run_user_level_audit(events)
    assert result.total_matched_orders == 2
    assert result.cannibalized_orders == 0
