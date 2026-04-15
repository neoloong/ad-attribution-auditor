"""Tests for the organic baseline decision tree and regression/time-series methods."""

import numpy as np
import pandas as pd
import pytest

from ad_audit.engine.aggregate_audit import (
    _organic_baseline,
    _regression_baseline,
    _timeseries_interruption_baseline,
    _incremental_per_day,
)
from ad_audit.engine.models import AuditConfig


# ---------------------------------------------------------------------------
# _organic_baseline decision tree
# ---------------------------------------------------------------------------

def test_organic_baseline_falls_through_to_legacy():
    """Regression requires ≥60 days; time-series requires ≥7-day streak.
    Short data with no spend-off days → legacy returns 0.0."""
    daily = pd.DataFrame({
        "actual_conversions": [5.0, 5.0],
        "spend_on": [True, True],
    })
    baseline = _organic_baseline(daily)
    assert baseline == 0.0


def test_organic_baseline_legacy_spend_off_avg():
    """No regression (short data), no time-series (no 7+ streak) → legacy avg."""
    daily = pd.DataFrame({
        "actual_conversions": [5.0, 5.0, 5.0, 5.0],
        "spend_on": [True, True, False, False],
    })
    baseline = _organic_baseline(daily)
    assert baseline == 5.0  # avg of two off days


def test_organic_baseline_all_spend_on_returns_zero():
    """No spend-off days at all → 0.0."""
    daily = pd.DataFrame({
        "actual_conversions": [10.0, 20.0, 15.0],
        "spend_on": [True, True, True],
    })
    baseline = _organic_baseline(daily)
    assert baseline == 0.0


# ---------------------------------------------------------------------------
# _regression_baseline — failure paths
# ---------------------------------------------------------------------------

def test_regression_baseline_insufficient_days():
    """< 60 days → returns (0.0, None, 0.0)."""
    daily = pd.DataFrame({
        "spend": [0.0] * 30 + [100.0] * 29,
        "actual_conversions": [2.0] * 30 + [12.0] * 29,
    })
    # 59 rows < 60 MIN_DAYS → immediately returns (0.0, None, 0.0)
    assert len(daily) == 59
    intercept, method, r2 = _regression_baseline(daily)
    assert intercept == 0.0
    assert method is None
    assert r2 == 0.0


def test_regression_baseline_low_spend_variation():
    """spend std < 1.0 → returns (0.0, None, 0.0)."""
    daily = pd.DataFrame({
        "spend": [99.0] * 65,
        "actual_conversions": [10.0] * 65,
    })
    intercept, method, r2 = _regression_baseline(daily)
    assert method is None


def test_regression_baseline_insufficient_zero_spend_days():
    """< 3 zero-spend days → returns (0.0, None, 0.0)."""
    rng = np.random.default_rng(0)
    daily = pd.DataFrame({
        "spend": np.concatenate([[0.0, 0.0], rng.uniform(50, 200, 63)]),
        "actual_conversions": rng.uniform(2, 20, 65),
    })
    intercept, method, r2 = _regression_baseline(daily)
    assert method is None


def test_regression_baseline_negative_intercept():
    """OLS intercept < 0 → returns (0.0, None, 0.0)."""
    rng = np.random.default_rng(7)
    n = 65
    spend = np.concatenate([np.zeros(5), rng.uniform(50, 200, n - 5)])
    # Force negative intercept: conversions near 0 when spend=0,
    # but high values when spend is high (linear relationship offset)
    conv = -5.0 + 0.2 * spend + rng.normal(0, 1, n)
    daily = pd.DataFrame({"spend": spend, "actual_conversions": conv})
    intercept, method, r2 = _regression_baseline(daily)
    assert method is None


def test_regression_baseline_poor_r2():
    """R² < 0.01 (nearly flat/no relationship) → returns (0.0, None, 0.0)."""
    rng = np.random.default_rng(7)
    n = 65
    # Spend varies but conversions are random (low correlation)
    spend = rng.uniform(0, 200, n)
    conv = rng.normal(10, 5, n)  # uncorrelated with spend
    daily = pd.DataFrame({"spend": spend, "actual_conversions": conv})
    intercept, method, r2 = _regression_baseline(daily)
    assert method is None


def test_regression_baseline_success():
    """Valid regression: 60+ days, variation, zero-spend days, positive intercept, good R²."""
    rng = np.random.default_rng(7)
    n = 65
    # Strong relationship: conversions = 3 + 0.05 * spend + noise
    spend = np.concatenate([np.zeros(8), rng.uniform(20, 200, n - 8)])
    conv = 3.0 + 0.05 * spend + rng.normal(0, 0.5, n)
    daily = pd.DataFrame({"spend": spend, "actual_conversions": conv})
    intercept, method, r2 = _regression_baseline(daily)
    assert method == "regression"
    assert intercept > 0.0
    assert 0.0 <= r2 <= 1.0
    # Intercept should be close to 3.0 (organic baseline)
    assert intercept == pytest.approx(3.0, abs=1.0)


# ---------------------------------------------------------------------------
# _timeseries_interruption_baseline
# ---------------------------------------------------------------------------

def test_timeseries_interruption_no_qualifying_streak():
    """Longest spend-off streak is < 7 days → returns None."""
    daily = pd.DataFrame({
        "spend_on": [False, False, False, True, False, False, False, True, True],
        "actual_conversions": [5.0, 4.0, 6.0, 10.0, 3.0, 5.0, 4.0, 11.0, 9.0],
    })
    result = _timeseries_interruption_baseline(daily)
    assert result is None


def test_timeseries_interruption_qualifying_streak():
    """Spend-off streak ≥ 7 consecutive days → returns avg conversions during streak."""
    daily = pd.DataFrame({
        "spend_on": [True] * 5 + [False] * 8 + [True] * 5,
        "actual_conversions": [10.0] * 5 + [3.0, 4.0, 5.0, 3.0, 4.0, 5.0, 3.0, 4.0] + [12.0] * 5,
    })
    result = _timeseries_interruption_baseline(daily)
    assert result is not None
    # Off streak is [3,4,5,3,4,5,3,4], mean = 31/8 = 3.875
    assert result == pytest.approx(3.875)


def test_timeseries_interruption_exactly_7_days():
    """Exactly 7 spend-off days qualifies."""
    daily = pd.DataFrame({
        "spend_on": [True] * 10 + [False] * 7 + [True] * 5,
        "actual_conversions": [10.0] * 10 + [2.0] * 7 + [12.0] * 5,
    })
    result = _timeseries_interruption_baseline(daily)
    assert result == 2.0


# ---------------------------------------------------------------------------
# _incremental_per_day edge cases
# ---------------------------------------------------------------------------

def test_incremental_per_day_all_off():
    """No spend-on days → 0.0."""
    daily = pd.DataFrame({
        "actual_conversions": [10.0, 12.0, 8.0],
        "spend_on": [False, False, False],
    })
    result = _incremental_per_day(daily, organic_baseline=5.0)
    assert result == 0.0


def test_incremental_per_day_negative_delta():
    """Spend-on avg < organic baseline → clamped to 0.0."""
    daily = pd.DataFrame({
        "actual_conversions": [10.0, 12.0, 8.0],
        "spend_on": [True, True, True],
    })
    result = _incremental_per_day(daily, organic_baseline=50.0)
    assert result == 0.0
