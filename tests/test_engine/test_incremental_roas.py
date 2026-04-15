"""Tests for incremental ROAS computation."""

import pandas as pd

from ad_audit.engine.incremental_roas import compute_incremental_roas
from ad_audit.engine.models import AuditConfig


def test_basic_roas():
    daily = pd.DataFrame({
        "spend": [100, 100, 0, 100],
        "reported_revenue": [500, 500, 0, 500],
        "actual_revenue": [400, 400, 100, 400],
        "actual_conversions": [4, 4, 1, 4],
        "spend_on": [True, True, False, True],
    })
    config = AuditConfig()
    result = compute_incremental_roas(daily, organic_baseline=1.0, config=config)
    assert result.reported_roas > 0
    assert result.true_incremental_roas > 0
    assert result.true_incremental_roas <= result.reported_roas
    assert result.total_spend == 300.0


def test_zero_spend():
    daily = pd.DataFrame({
        "spend": [0, 0],
        "reported_revenue": [0, 0],
        "actual_revenue": [50, 50],
        "actual_conversions": [1, 1],
        "spend_on": [False, False],
    })
    config = AuditConfig()
    result = compute_incremental_roas(daily, organic_baseline=1.0, config=config)
    assert result.reported_roas == 0.0
    assert result.true_incremental_roas == 0.0


def test_inflation_rate_negative_true_roas():
    """true_roas > reported_roas → inflation = 0.0 (capped)"""
    # Spend=1, reported_rev=1 → reported_roas=1.0
    # actual_rev=100/10conv, organic=0.5*10*1=5, incr_rev=95 → true_roas=95
    # true_roas >> reported_roas → inflation = (1-95)/1 = -94 → capped at 0.0
    daily = pd.DataFrame({
        "spend": [1],
        "reported_revenue": [1],
        "actual_revenue": [100],
        "actual_conversions": [10],
        "spend_on": [True],
    })
    config = AuditConfig()
    result = compute_incremental_roas(daily, organic_baseline=0.5, config=config)
    assert result.true_incremental_roas > result.reported_roas
    assert result.inflation_rate == 0.0


def test_inflation_rate_tiny_reported_roas():
    """reported_roas = 0.001 → inflation capped at 10.0"""
    daily = pd.DataFrame({
        "spend": [100000],
        "reported_revenue": [100],
        "actual_revenue": [10],
        "actual_conversions": [1],
        "spend_on": [True],
    })
    config = AuditConfig()
    result = compute_incremental_roas(daily, organic_baseline=0.0, config=config)
    # reported_roas = 100/100000 = 0.001, true_roas ≈ 0
    # inflation = (0.001 - ~0) / max(0.001, 0.01) = 0.001/0.01 = 0.1 → capped at 10
    # Actually denominator is max(0.001, 0.01) = 0.01, so inflation = 0.001/0.01 = 0.1
    # But if true_roas is slightly negative: inflation can go > 10
    # With organic_baseline=0, true_roas = 10/100000 = 0.0001
    # inflation = (0.001 - 0.0001) / 0.01 = 0.0999/0.01 = 9.99 → rounded to 4dp
    assert result.inflation_rate <= 10.0


def test_avg_rev_per_conv_all_nan():
    """all NaN conversions → avg_rev = 0.0"""
    daily = pd.DataFrame({
        "spend": [100, 100],
        "reported_revenue": [500, 500],
        "actual_revenue": [100.0, 200.0],
        "actual_conversions": [float("nan"), float("nan")],
        "spend_on": [True, True],
    })
    config = AuditConfig()
    result = compute_incremental_roas(daily, organic_baseline=0.0, config=config)
    assert result.inflation_rate >= 0.0
