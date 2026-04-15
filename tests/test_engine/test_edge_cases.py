"""Boundary / edge-case tests for core engine modules."""

import numpy as np
import pandas as pd

from ad_audit.engine.incremental_roas import compute_incremental_roas
from ad_audit.engine.user_level_audit import _match_purchases_to_clicks
from ad_audit.engine.models import AuditConfig


# ---------------------------------------------------------------------------
# compute_incremental_roas edge cases
# ---------------------------------------------------------------------------

def test_incremental_roas_zero_conversions_nonzero_revenue():
    """actual_conversions=0 but revenue>0 → avg_rev=inf guard returns safely."""
    daily = pd.DataFrame({
        "spend": [100.0],
        "reported_revenue": [500.0],
        "actual_revenue": [300.0],
        "actual_conversions": [0],
        "spend_on": [True],
    })
    config = AuditConfig()
    result = compute_incremental_roas(daily, organic_baseline=1.0, config=config)
    assert result.reported_roas == 5.0
    assert result.true_incremental_roas >= 0.0
    assert result.inflation_rate >= 0.0


def test_incremental_roas_nan_conversions():
    """actual_conversions is NaN → avg_rev=0, no crash."""
    daily = pd.DataFrame({
        "spend": [100.0],
        "reported_revenue": [500.0],
        "actual_revenue": [300.0],
        "actual_conversions": [float("nan")],
        "spend_on": [True],
    })
    config = AuditConfig()
    result = compute_incremental_roas(daily, organic_baseline=1.0, config=config)
    assert result.reported_roas == 5.0
    assert result.incremental_revenue >= 0.0


def test_incremental_roas_organic_exceeds_actual():
    """organic_revenue > actual_revenue_on → incremental=0, inflation=1.0."""
    daily = pd.DataFrame({
        "spend": [100.0],
        "reported_revenue": [100.0],
        "actual_revenue": [50.0],
        "actual_conversions": [1],
        "spend_on": [True],
    })
    config = AuditConfig()
    result = compute_incremental_roas(daily, organic_baseline=10.0, config=config)
    # organic_revenue = 10 * 50 * 1 = 500 > actual 50 → incr = 0
    assert result.incremental_revenue == 0.0
    assert result.inflation_rate == 1.0


def test_incremental_roas_tiny_reported_roas_capped():
    """reported_roas is tiny → inflation capped at 10.0 (not exploding)."""
    daily = pd.DataFrame({
        "spend": [1_000_000.0],
        "reported_revenue": [100.0],  # roas = 0.0001
        "actual_revenue": [10.0],
        "actual_conversions": [1],
        "spend_on": [True],
    })
    config = AuditConfig()
    result = compute_incremental_roas(daily, organic_baseline=0.0, config=config)
    assert result.inflation_rate <= 10.0


def test_incremental_roas_zero_spend_days():
    """All days are spend-off → reported_roas=0, true_roas=0, inflation=0."""
    daily = pd.DataFrame({
        "spend": [0.0, 0.0],
        "reported_revenue": [0.0, 0.0],
        "actual_revenue": [100.0, 200.0],
        "actual_conversions": [1, 2],
        "spend_on": [False, False],
    })
    config = AuditConfig()
    result = compute_incremental_roas(daily, organic_baseline=1.5, config=config)
    assert result.reported_roas == 0.0
    assert result.true_incremental_roas == 0.0


# ---------------------------------------------------------------------------
# _match_purchases_to_clicks edge cases
# ---------------------------------------------------------------------------

def test_match_empty_clicks():
    """clicks is empty DataFrame → returns empty DataFrame, no crash."""
    clicks = pd.DataFrame(columns=["email_hash", "timestamp", "user_id", "revenue"])
    purchases = pd.DataFrame({
        "user_id": ["u1", "u2"],
        "email_hash": ["h1", "h2"],
        "timestamp": pd.to_datetime(["2024-01-01", "2024-01-02"]),
        "revenue": [50.0, 75.0],
    })
    config = AuditConfig()
    result = _match_purchases_to_clicks(clicks, purchases, config)
    assert result.empty


def test_match_empty_purchases():
    """purchases is empty DataFrame → returns empty DataFrame, no crash."""
    clicks = pd.DataFrame({
        "user_id": ["u1"],
        "email_hash": ["h1"],
        "timestamp": pd.to_datetime(["2024-01-01"]),
        "revenue": [0.0],
    })
    purchases = pd.DataFrame(columns=["email_hash", "timestamp", "user_id", "revenue"])
    config = AuditConfig()
    result = _match_purchases_to_clicks(clicks, purchases, config)
    assert result.empty


def test_match_both_empty():
    """Both DataFrames empty → returns empty DataFrame."""
    clicks = pd.DataFrame(columns=["email_hash", "timestamp", "user_id", "revenue"])
    purchases = pd.DataFrame(columns=["email_hash", "timestamp", "user_id", "revenue"])
    config = AuditConfig()
    result = _match_purchases_to_clicks(clicks, purchases, config)
    assert result.empty


# ---------------------------------------------------------------------------
# NaN / date discontinuity in daily DataFrame
# ---------------------------------------------------------------------------

def test_build_daily_handles_nan_spend():
    """NaN spend in ad_df is filled with 0 during merge."""
    from ad_audit.engine.aggregate_audit import _build_daily_merged

    ad_df = pd.DataFrame({
        "date": pd.date_range("2024-01-01", periods=3),
        "spend": [100.0, float("nan"), 200.0],
        "reported_conversions": [5, 3, 10],
        "reported_revenue": [500.0, 300.0, 1000.0],
        "platform": "meta",
    })
    shopify_df = pd.DataFrame({
        "date": pd.date_range("2024-01-01", periods=3),
        "revenue": [100.0, 200.0, 300.0],
    })
    daily = _build_daily_merged(ad_df, shopify_df, None)
    assert daily["spend"].isna().sum() == 0  # NaN filled with 0


def test_daily_date_gaps_filled():
    """Non-continuous dates are preserved (outer merge keeps all dates)."""
    from ad_audit.engine.aggregate_audit import _build_daily_merged

    ad_df = pd.DataFrame({
        "date": pd.to_datetime(["2024-01-01", "2024-01-05", "2024-01-10"]),
        "spend": [100.0, 150.0, 200.0],
        "reported_conversions": [5, 7, 10],
        "reported_revenue": [500.0, 700.0, 1000.0],
        "platform": "meta",
    })
    shopify_df = pd.DataFrame({
        "date": pd.to_datetime(["2024-01-01", "2024-01-05", "2024-01-10"]),
        "revenue": [100.0, 200.0, 300.0],
    })
    daily = _build_daily_merged(ad_df, shopify_df, None)
    assert len(daily) == 3
    assert [d.day for d in daily["date"]] == [1, 5, 10]
