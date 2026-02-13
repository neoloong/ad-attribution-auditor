"""Tests for aggregate audit engine."""

import numpy as np
import pandas as pd
import pytest

from ad_audit.engine.aggregate_audit import (
    run_aggregate_audit,
    _build_daily_merged,
    _organic_baseline,
    _incremental_per_day,
    _rolling_correlation,
)
from ad_audit.engine.models import AuditConfig, AuditMode


def test_build_daily_merged(sample_meta_ads_df, sample_shopify_orders_df, sample_gsc_df):
    daily = _build_daily_merged(sample_meta_ads_df, sample_shopify_orders_df, sample_gsc_df)
    assert "spend" in daily.columns
    assert "actual_conversions" in daily.columns
    assert "brand_clicks" in daily.columns
    assert daily["spend"].dtype == float or daily["spend"].dtype == np.float64


def test_organic_baseline():
    daily = pd.DataFrame({
        "actual_conversions": [10, 12, 0, 8, 0],
        "spend_on": [True, True, False, True, False],
    })
    baseline = _organic_baseline(daily)
    assert baseline == 0.0  # avg of [0, 0]


def test_organic_baseline_with_values():
    daily = pd.DataFrame({
        "actual_conversions": [10, 12, 5, 8, 3],
        "spend_on": [True, True, False, True, False],
    })
    baseline = _organic_baseline(daily)
    assert baseline == 4.0  # avg of [5, 3]


def test_incremental_per_day():
    daily = pd.DataFrame({
        "actual_conversions": [10, 12, 5, 8, 3],
        "spend_on": [True, True, False, True, False],
    })
    baseline = 4.0
    incr = _incremental_per_day(daily, baseline)
    assert incr == pytest.approx(10.0 - 4.0)  # avg([10,12,8]) - 4


def test_rolling_correlation():
    daily = pd.DataFrame({
        "spend": [0, 0, 100, 100, 200, 200, 0, 0, 0, 0],
        "actual_conversions": [1, 1, 5, 6, 10, 11, 2, 1, 1, 1],
    })
    corr = _rolling_correlation(daily, 5)
    assert -1.0 <= corr <= 1.0
    assert corr > 0.5  # Spend and conversions positively correlated


def test_run_aggregate_audit(sample_meta_ads_df, sample_shopify_orders_df, sample_gsc_df):
    config = AuditConfig(mode=AuditMode.AGGREGATE)
    result = run_aggregate_audit(
        sample_meta_ads_df, sample_shopify_orders_df, sample_gsc_df, config
    )
    assert result.mode == AuditMode.AGGREGATE
    assert result.daily_df is not None
    assert result.incremental_roas.total_spend > 0
    assert 0 <= result.incremental_roas.inflation_rate <= 1.0
    assert result.organic_baseline_conversions >= 0


def test_no_gsc(sample_meta_ads_df, sample_shopify_orders_df):
    """Aggregate audit works without GSC data (graceful degradation)."""
    config = AuditConfig(mode=AuditMode.AGGREGATE)
    result = run_aggregate_audit(
        sample_meta_ads_df, sample_shopify_orders_df, None, config
    )
    assert result.mode == AuditMode.AGGREGATE
    assert result.daily_df is not None
    assert "brand_clicks" not in result.daily_df.columns
    assert result.cannibalization.cannibalization_score == 0.0
    assert result.incremental_roas.total_spend > 0


def test_multi_platform(sample_meta_ads_df, sample_google_ads_df, sample_shopify_orders_df, sample_gsc_df):
    """Aggregate audit works with both Meta + Google Ads combined."""
    import pandas as pd
    ad_df = pd.concat([sample_meta_ads_df, sample_google_ads_df], ignore_index=True)
    config = AuditConfig(mode=AuditMode.AGGREGATE)
    result = run_aggregate_audit(ad_df, sample_shopify_orders_df, sample_gsc_df, config)
    assert result.mode == AuditMode.AGGREGATE
    assert result.daily_df is not None
    assert result.incremental_roas.total_spend > 0
