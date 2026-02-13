"""Tests for cannibalization scoring."""

import pandas as pd

from ad_audit.engine.cannibalization import compute_cannibalization
from ad_audit.engine.models import AuditConfig


def test_no_cannibalization():
    daily = pd.DataFrame({
        "reported_conversions": [5, 5, 5],
        "brand_clicks": [1, 1, 1],
        "spend_on": [True, True, True],
        "spend": [100, 100, 100],
        "actual_revenue": [500, 500, 500],
    })
    config = AuditConfig(rolling_avg_days=3)
    result = compute_cannibalization(daily, config)
    # All values at or below average → no cannibalization
    assert result.cannibalized_days == 0


def test_cannibalization_detected():
    daily = pd.DataFrame({
        "reported_conversions": [2, 2, 2, 10, 10],
        "brand_clicks": [3, 3, 3, 15, 15],
        "spend_on": [True, True, True, True, True],
        "spend": [100] * 5,
        "actual_revenue": [200, 200, 200, 1000, 1000],
    })
    config = AuditConfig(rolling_avg_days=3)
    result = compute_cannibalization(daily, config)
    assert result.cannibalized_days > 0
    assert result.cannibalization_score > 0


def test_empty_brand_clicks():
    daily = pd.DataFrame({
        "reported_conversions": [5],
        "spend_on": [True],
        "spend": [100],
        "actual_revenue": [500],
    })
    config = AuditConfig()
    result = compute_cannibalization(daily, config)
    assert result.cannibalization_score == 0.0
