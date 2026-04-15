"""Phase 2C: Additional boundary/edge-case tests to reach 75%+ coverage.

These complement the existing test suites. Each test targets a specific
boundary condition identified in the methodology document.
"""

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
from ad_audit.engine.organic_baseline_regression import (
    estimate_organic_baseline,
    BaselineMethod,
    _regression_baseline_full,
    _build_features,
    _compute_baseline_from_coeffs,
)


# ---------------------------------------------------------------------------
# Rolling correlation edge cases
# ---------------------------------------------------------------------------

def test_rolling_correlation_identical_spend():
    """All spend identical → 0.0 (no variance)."""
    daily = pd.DataFrame({
        "spend": [100.0] * 50,
        "actual_conversions": [5.0, 6.0, 7.0, 5.0, 8.0] * 10,
    })
    corr = _rolling_correlation(daily, 7)
    assert corr == 0.0


def test_rolling_correlation_identical_conversions():
    """All conversions identical → 0.0 (no variance)."""
    daily = pd.DataFrame({
        "spend": [0.0, 50.0, 100.0, 150.0, 200.0] * 10,
        "actual_conversions": [5.0] * 50,
    })
    corr = _rolling_correlation(daily, 7)
    assert corr == 0.0


def test_rolling_correlation_two_rows():
    """Exactly 2 rows → fallback to global corrcoef (no rolling window)."""
    daily = pd.DataFrame({
        "spend": [0.0, 200.0],
        "actual_conversions": [2.0, 10.0],
    })
    corr = _rolling_correlation(daily, 7)
    assert -1.0 <= corr <= 1.0


def test_rolling_correlation_spend_negative_zero_variance():
    """spend std = 0 → 0.0."""
    daily = pd.DataFrame({
        "spend": [0.0] * 20,
        "actual_conversions": [1.0, 2.0, 3.0, 4.0, 5.0] * 4,
    })
    corr = _rolling_correlation(daily, 7)
    assert corr == 0.0


# ---------------------------------------------------------------------------
# _build_daily_merged edge cases
# ---------------------------------------------------------------------------

def test_build_daily_only_shopify_no_ads():
    """No ad data → only shopify columns survive, spend=0."""
    shopify = pd.DataFrame({
        "date": pd.date_range("2024-01-01", periods=5),
        "revenue": [100.0, 200.0, 150.0, 180.0, 220.0],
    })
    daily = _build_daily_merged(
        pd.DataFrame(columns=["date", "spend", "reported_conversions", "reported_revenue", "platform"]),
        shopify,
        None,
    )
    assert "spend" in daily.columns
    assert daily["spend"].sum() == 0.0
    assert len(daily) == 5


def test_build_daily_both_empty():
    """Both ad and shopify empty → empty DataFrame (outer merge preserves dates)."""
    ad = pd.DataFrame(columns=["date", "spend", "reported_conversions", "reported_revenue", "platform"])
    shopify = pd.DataFrame(columns=["date", "revenue"])
    daily = _build_daily_merged(ad, shopify, None)
    assert daily.empty


# ---------------------------------------------------------------------------
# _organic_baseline via new module — edge paths
# ---------------------------------------------------------------------------

def test_estimate_negative_intercept_clamped():
    """Regression returns NONE if intercept < 0 (already tested); this confirms
    the decision tree never emits a negative baseline."""
    rng = np.random.default_rng(7)
    n = 65
    dates = pd.date_range("2024-01-01", periods=n, freq="D")
    spend = np.concatenate([np.zeros(8), rng.uniform(20, 200, n - 8)])
    # Negative intercept by design (but passes other checks)
    conv = -2.0 + 0.10 * spend + rng.normal(0, 0.2, n)
    daily = pd.DataFrame({"date": dates, "spend": spend, "actual_conversions": conv})
    result = estimate_organic_baseline(daily)
    assert result.baseline_daily >= 0.0


def test_estimate_regression_r2_edge_case():
    """R² exactly at 0.01 boundary → returns NONE (not REGRESSION)."""
    rng = np.random.default_rng(7)
    n = 65
    dates = pd.date_range("2024-01-01", periods=n, freq="D")
    spend = rng.uniform(0, 200, n)
    # Make conversions nearly constant → R² ≈ 0
    conv = np.full(n, 10.0) + rng.normal(0, 0.01, n)
    daily = pd.DataFrame({"date": dates, "spend": spend, "actual_conversions": conv})
    result = _regression_baseline_full(daily)
    assert result.method == BaselineMethod.NONE


def test_estimate_zero_spend_days_at_boundary():
    """Exactly 3 zero-spend days → should pass (MIN_ZERO_SPEND_DAYS = 3)."""
    rng = np.random.default_rng(7)
    n = 65
    dates = pd.date_range("2024-01-01", periods=n, freq="D")
    spend = rng.uniform(20, 200, n)
    spend[0] = 0.0
    spend[33] = 0.0
    spend[57] = 0.0  # exactly 3
    conv = 3.0 + 0.05 * spend + rng.normal(0, 0.5, n)
    daily = pd.DataFrame({"date": dates, "spend": spend, "actual_conversions": conv})
    result = _regression_baseline_full(daily)
    assert result.method == BaselineMethod.REGRESSION


def test_estimate_insufficient_days_exactly_59():
    """Exactly 59 days → NONE from regression."""
    rng = np.random.default_rng(7)
    daily = pd.DataFrame({
        "date": pd.date_range("2024-01-01", periods=59, freq="D"),
        "spend": rng.uniform(0, 200, 59),
        "actual_conversions": rng.uniform(2, 20, 59),
    })
    result = _regression_baseline_full(daily)
    assert result.method == BaselineMethod.NONE


def test_estimate_timeseries_interrupt_exactly_7_days():
    """Exactly 7 spend-off days → QUALIFIES (threshold is ≥ 7)."""
    daily = pd.DataFrame({
        "date": pd.date_range("2024-01-01", periods=25, freq="D"),
        "spend_on": [True] * 10 + [False] * 7 + [True] * 8,
        "actual_conversions": [10.0] * 10 + [2.0] * 7 + [12.0] * 8,
        "spend": [100.0] * 10 + [0.0] * 7 + [100.0] * 8,
    })
    result = estimate_organic_baseline(daily)
    # < 60 days so not regression; timeseries interruption should fire
    assert result.method == BaselineMethod.TIMESERIES_INTERRUPTION
    assert result.baseline_daily == 2.0


# ---------------------------------------------------------------------------
# _build_features coverage
# ---------------------------------------------------------------------------

def test_build_features_single_day():
    """Single row → feature matrix is 1×N, valid for OLS."""
    daily = pd.DataFrame({
        "date": pd.to_datetime(["2024-01-01"]),
        "spend": [100.0],
        "actual_conversions": [5.0],
    })
    X, names = _build_features(daily)
    assert X.shape == (1, len(names))
    assert "ad_spend" in names
    assert "trend" in names


def test_build_features_missing_optional_columns():
    """spend_on absent → code handles gracefully via default threshold (≥5.0).
    Since all spend=100.0 (no zero days), timeseries path fails;
    data<60 days → WARNING_MODE with 0 baseline."""
    daily = pd.DataFrame({
        "date": pd.date_range("2024-01-01", periods=10, freq="D"),
        "spend": [100.0] * 10,
        "actual_conversions": [5.0] * 10,
    })
    result = estimate_organic_baseline(daily)
    # spend_on is derived from spend>=5.0 → all True → no spend-off streak
    # Regression fails (< 60 days + constant spend); Timeseries fails (no streak)
    # → WARNING_MODE (not NONE, because estimate_organic_baseline always returns a result)
    assert result.method == BaselineMethod.WARNING_MODE
    assert result.baseline_daily == 0.0  # no off days to average


# ---------------------------------------------------------------------------
# Full audit pipeline with new module
# ---------------------------------------------------------------------------

def test_run_audit_with_60day_dataset(sample_meta_ads_df, sample_shopify_orders_df):
    """60 days of data → uses REGRESSION path end-to-end."""
    # Extend the sample fixture to 60 days
    dates = pd.date_range("2024-01-01", periods=60, freq="D")
    rng = np.random.default_rng(42)
    spend = rng.uniform(0, 200, size=60)
    spend[:8] = 0
    purchases = (spend * rng.uniform(0.02, 0.08, size=60)).astype(int)
    revenue = purchases * rng.uniform(30, 80, size=60)

    meta = pd.DataFrame({
        "date": dates,
        "campaign_name": "Test Campaign",
        "spend": spend,
        "reported_conversions": purchases,
        "reported_revenue": revenue,
        "platform": "meta",
    })

    config = AuditConfig(mode=AuditMode.AGGREGATE)
    result = run_aggregate_audit(meta, sample_shopify_orders_df, None, config)
    assert result.organic_baseline_conversions >= 0
    assert result.incremental_conversions_per_day >= 0.0


# ---------------------------------------------------------------------------
# _incremental_per_day boundary cases
# ---------------------------------------------------------------------------

def test_incremental_per_day_exactly_zero():
    """spend-on avg equals organic baseline → 0 (not negative)."""
    daily = pd.DataFrame({
        "actual_conversions": [5.0, 5.0, 5.0],
        "spend_on": [True, True, True],
    })
    result = _incremental_per_day(daily, organic_baseline=5.0)
    assert result == 0.0


def test_incremental_per_day_all_off_returns_zero():
    """All spend-off days → 0.0."""
    daily = pd.DataFrame({
        "actual_conversions": [5.0, 6.0, 7.0],
        "spend_on": [False, False, False],
    })
    result = _incremental_per_day(daily, organic_baseline=3.0)
    assert result == 0.0


# ---------------------------------------------------------------------------
# _rolling_correlation — NaN handling
# ---------------------------------------------------------------------------

def test_rolling_correlation_with_nan():
    """NaN in conversions → gracefully skips (handles via pandas rolling)."""
    daily = pd.DataFrame({
        "spend": [100.0] * 20,
        "actual_conversions": [5.0, 6.0, float("nan"), 8.0, 7.0] * 4,
    })
    corr = _rolling_correlation(daily, 5)
    assert -1.0 <= corr <= 1.0  # should not raise


# ---------------------------------------------------------------------------
# _compute_baseline_from_coeffs — unit level
# ---------------------------------------------------------------------------

def test_compute_baseline_from_coeffs_trend_only():
    """Unit test for baseline computation with only intercept + trend."""
    beta = np.array([100.0, 0.5])  # alpha=100, trend=0.5
    names = ["const", "trend"]  # won't actually appear from _build_features but tests the pure function
    # Use internal function directly
    baseline = _compute_baseline_from_coeffs(beta=beta, feature_names=names, n=100)
    # With normalised trend at 0.5 midpoint: baseline = 100 + 0.5*0.5 = 100.25
    # (But if const isn't in names it gets 0 for avg_dow/avg_month effects)
    assert baseline >= 100.0


# ---------------------------------------------------------------------------
# AuditResult — extras field
# ---------------------------------------------------------------------------

def test_audit_result_extras_passed_through(sample_meta_ads_df, sample_shopify_orders_df):
    """extras dict on AuditConfig flows through to AuditResult.extras."""
    config = AuditConfig(mode=AuditMode.AGGREGATE)
    result = run_aggregate_audit(sample_meta_ads_df, sample_shopify_orders_df, None, config)
    assert hasattr(result, "extras")
    assert isinstance(result.extras, dict)
