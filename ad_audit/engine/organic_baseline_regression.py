"""Organic baseline estimation via regression with seasonal controls.

This module replaces the simple bivariate OLS in _regression_baseline with a
full multivariate regression::

    Sales(t) = α + β·AdSpend(t)
               + Σγ_j·DOW_j  (day-of-week dummies)
               + Σδ_k·Month_k  (month-of-year dummies)
               + θ·t  (linear trend)
               + ε

The organic baseline is the intercept α — the expected sales when ad spend
is zero, controlling for day-of-week effects, seasonality, and trends.

Fallback decision tree (in priority order)
------------------------------------------
1. Regression  — data ≥ 60 days + spend has variation
2. Time-Series Interruption — clear spend drop ≥ 70% lasting ≥ 7 days
3. Warning mode — data < 60 days (result returned with warning flag)

References
----------
See /Users/chao/.openclaw/workspace/memory/projects/ad-attribution-baseline-methodology.md
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

import numpy as np
import pandas as pd


class BaselineMethod(str, Enum):
    REGRESSION = "regression"
    TIMESERIES_INTERRUPTION = "timeseries_interruption"
    WARNING_MODE = "warning_mode"
    NONE = "none"


@dataclass
class BaselineResult:
    """Result of organic baseline estimation."""

    # Estimated avg daily organic conversions
    baseline_daily: float = 0.0

    # Method that was used
    method: BaselineMethod = BaselineMethod.NONE

    # R² of the regression model (0 if not regression)
    r_squared: float = 0.0

    # Ad spend coefficient — marginal conversions per dollar
    ad_marginal_effect: float = 0.0

    # Number of observations used
    n_obs: int = 0

    # Any warning messages
    warnings: list[str] = field(default_factory=list)

    # Human-readable model summary (regression only)
    model_summary: str = ""

    @property
    def method_label(self) -> str:
        return self.method.value


# ---------------------------------------------------------------------------
# Decision tree router
# ---------------------------------------------------------------------------

MIN_DAYS_REGRESSION = 60
MIN_SPEND_STD = 1.0
MIN_ZERO_SPEND_DAYS = 3
MIN_INTERRUPTION_DAYS = 7
INTERRUPTION_SPEND_DROP_FRAC = 0.70
MIN_INTERRUPTION_LENGTH_DAYS = 7


def estimate_organic_baseline(daily: pd.DataFrame) -> BaselineResult:
    """Estimate organic baseline using the fallback decision tree.

    Parameters
    ----------
    daily : pd.DataFrame
        Must contain columns: ``date``, ``spend``, ``actual_conversions``.
        ``spend_on`` column is also used if present.

    Returns
    -------
    BaselineResult
    """
    # Ensure required columns exist
    if "spend" not in daily.columns or "actual_conversions" not in daily.columns:
        return _result_none(warnings=["Missing required columns: spend, actual_conversions"])

    # Add spend_on column if not present
    if "spend_on" not in daily.columns:
        _daily = daily.copy()
        _daily["spend_on"] = _daily["spend"] >= 5.0
    else:
        _daily = daily

    # ---- Method 1: Regression (full multivariate) ----
    reg_result = _regression_baseline_full(_daily)
    if reg_result.method == BaselineMethod.REGRESSION:
        return reg_result

    # ---- Method 2: Time-Series Interruption ----
    ts_result = _timeseries_interruption_baseline(_daily)
    if ts_result.method == BaselineMethod.TIMESERIES_INTERRUPTION:
        return ts_result

    # ---- Method 3: Warning mode (insufficient data) ----
    return _warning_mode_fallback(_daily)


# ---------------------------------------------------------------------------
# Method 1 — Full multivariate regression
# ---------------------------------------------------------------------------

def _regression_baseline_full(daily: pd.DataFrame) -> BaselineResult:
    """Full OLS regression with DOW, month, and trend controls.

    Requires:
    - ≥ 60 days of data
    - Spend variation (std ≥ 1.0)
    - At least 3 zero-spend days
    - Non-negative intercept
    - R² ≥ 0.01

    Returns
    -------
    BaselineResult with method REGRESSION on success, NONE on failure.
    """
    spend = daily["spend"].values
    conv = daily["actual_conversions"].values
    dates = daily["date"]

    # ---- Data quality gate ----
    if len(daily) < MIN_DAYS_REGRESSION:
        return _result_none(warnings=[f"Data insufficient: {len(daily)} days < {MIN_DAYS_REGRESSION} required"])

    if spend.std() < MIN_SPEND_STD:
        return _result_none(warnings=["Spend has no variation (std < 1.0)"])

    zero_spend_days = int(np.sum(spend == 0))
    if zero_spend_days < MIN_ZERO_SPEND_DAYS:
        return _result_none(warnings=[f"Too few zero-spend days: {zero_spend_days} < {MIN_ZERO_SPEND_DAYS} required"])

    # ---- Build feature matrix ----
    X, feature_names = _build_features(daily)
    y = conv

    # ---- OLS via normal equations ----
    try:
        # Suppress spurious numpy/Accelerate warnings from internal float-accumulation
        with np.errstate(divide='ignore', over='ignore', invalid='ignore'):
            XtX = X.T @ X
        # Guard against overflow / singular matrix
        XtX_det = np.linalg.det(XtX)
        if not np.isfinite(XtX_det) or abs(XtX_det) < 1e-12:
            return _result_none(warnings=["OLS matrix near-singular (overflow or perfect collinearity)"])
        with np.errstate(divide='ignore', over='ignore', invalid='ignore'):
            Xty = X.T @ y
        beta = np.linalg.solve(XtX, Xty)
        if not np.isfinite(beta).all():
            return _result_none(warnings=["OLS solution not finite"])
    except np.linalg.LinAlgError:
        return _result_none(warnings=["OLS solution failed (singular matrix)"])

    intercept = beta[0]
    if intercept < 0:
        return _result_none(warnings=[f"Negative intercept clamped to 0: {intercept:.2f}"])

    # ---- R² check ----
    with np.errstate(divide='ignore', over='ignore', invalid='ignore'):
        y_hat = X @ beta
    ss_res = np.sum((y - y_hat) ** 2)
    ss_tot = np.sum((y - y.mean()) ** 2)
    r2 = 1.0 - (ss_res / ss_tot) if ss_tot > 0 else 0.0

    if r2 < 0.01:
        return _result_none(warnings=[f"Poor model fit: R² = {r2:.4f} < 0.01"])

    # ---- Durbin-Watson for residual autocorrelation ----
    residuals = y - y_hat
    dw = _durbin_watson(residuals)
    dw_warnings = []
    if dw < 1.5:
        dw_warnings.append(f"Residual autocorrelation detected: Durbin-Watson = {dw:.2f} < 1.5")

    # ---- Baseline = intercept + average control-variable effects ----
    baseline = _compute_baseline_from_coeffs(
        beta=beta,
        feature_names=feature_names,
        n=len(daily),
    )

    ad_marginal_idx = feature_names.index("ad_spend") if "ad_spend" in feature_names else None
    # beta is for normalised ad_spend [0,1]; convert back to "per dollar" scale
    raw_spend_max = max(np.maximum(daily["spend"].values, 0.0).max(), 1e-8)
    ad_marginal = float(beta[ad_marginal_idx]) / raw_spend_max if ad_marginal_idx is not None else 0.0

    summary = (
        f"Multivariate OLS Regression (n={len(daily)})\n"
        f"  Intercept (baseline) = {intercept:.4f}\n"
        f"  Ad spend coefficient = {ad_marginal:.6f}\n"
        f"  R² = {r2:.4f}\n"
        f"  Durbin-Watson = {dw:.3f}\n"
    )

    return BaselineResult(
        baseline_daily=max(0.0, baseline),
        method=BaselineMethod.REGRESSION,
        r_squared=float(r2),
        ad_marginal_effect=ad_marginal,
        n_obs=len(daily),
        warnings=dw_warnings,
        model_summary=summary,
    )


def _build_features(daily: pd.DataFrame) -> tuple[np.ndarray, list[str]]:
    """Build feature matrix for OLS regression.

    Returns (X, feature_names) where X has shape (n_obs, n_features).
    """
    n = len(daily)
    features: dict[str, np.ndarray] = {}

    # Core variable: ad spend (clipped to 0 — can't be negative)
    # Normalise to [0,1] to prevent overflow in X.T @ X (same reason as trend)
    raw_spend = np.maximum(daily["spend"].values, 0.0)
    max_spend = max(raw_spend.max(), 1e-8)  # avoid div-by-zero
    features["ad_spend"] = raw_spend / max_spend

    # Day-of-week dummies (0=Mon, …, 6=Sun); drop_first to avoid multicollinearity
    dow = pd.get_dummies(daily["date"].dt.dayofweek, prefix="dow", drop_first=True, dtype=float)
    for col in dow.columns:
        features[col] = dow[col].values

    # Month-of-year dummies; drop_first
    month = pd.get_dummies(daily["date"].dt.month, prefix="month", drop_first=True, dtype=float)
    for col in month.columns:
        features[col] = month[col].values

    # Linear trend (days from start, normalised to [0,1] to avoid overflow)
    features["trend"] = np.arange(n, dtype=float) / max(n - 1, 1)

    # Assemble matrix
    feature_names = list(features.keys())
    X = np.column_stack([features[name] for name in feature_names])

    return X, feature_names


def _compute_baseline_from_coeffs(
    beta: np.ndarray,
    feature_names: list[str],
    n: int,
) -> float:
    """Compute baseline from regression coefficients.

    Baseline = α + avg_DOW_effect + avg_month_effect + trend_effect_at_midpoint

    The control-variable effects are averaged assuming a "typical" day
    (uniform distribution across DOW and month).
    """
    alpha = beta[0]

    # Average DOW effect (dow_1 … dow_6; dow_0 is reference)
    dow_indices = [i for i, name in enumerate(feature_names) if name.startswith("dow_")]
    avg_dow = np.mean([beta[i] for i in dow_indices]) if dow_indices else 0.0

    # Average month effect (month_2 … month_12; month_1 is reference)
    month_indices = [i for i, name in enumerate(feature_names) if name.startswith("month_")]
    avg_month = np.mean([beta[i] for i in month_indices]) if month_indices else 0.0

    # Trend effect at midpoint of data
    trend_idx = feature_names.index("trend") if "trend" in feature_names else None
    trend_mid = (n - 1) / 2
    trend_effect = beta[trend_idx] * trend_mid if trend_idx is not None else 0.0

    return float(alpha + avg_dow + avg_month + trend_effect)


def _durbin_watson(residuals: np.ndarray) -> float:
    """Durbin-Watson statistic for residual autocorrelation.

    Values near 2.0 → no autocorrelation.
    Values < 1.5 → possible positive autocorrelation.
    Values > 2.5 → possible negative autocorrelation.
    """
    diff = np.diff(residuals)
    Numerator = np.sum(diff**2)
    Denominator = np.sum(residuals**2)
    return float(Numerator / Denominator) if Denominator > 0 else 2.0


# ---------------------------------------------------------------------------
# Method 2 — Time-series interruption detection
# ---------------------------------------------------------------------------

def _timeseries_interruption_baseline(daily: pd.DataFrame) -> BaselineResult:
    """Detect clear, sustained spend drop and use pre-/post- comparison.

    Looks for a spend drop of ≥ 70% lasting ≥ 7 consecutive days.
    Falls back to the legacy spend-off streak check (≥ 7 consecutive spend_on=False days).

    Returns BaselineResult with method TIMESERIES_INTERRUPTION on success,
    NONE if no qualifying pattern found.
    """
    spend = daily["spend"].values
    conv = daily["actual_conversions"].values
    n = len(spend)

    # ---- Primary: detect ≥ 70% spend drop lasting ≥ 7 days ----
    drop_baseline = _detect_spend_drop(daily)
    if drop_baseline is not None:
        return drop_baseline

    # ---- Legacy: longest spend-off streak ----
    if "spend_on" in daily.columns:
        spend_on = daily["spend_on"].values
    else:
        spend_on = spend >= 5.0

    best_start = -1
    best_len = 0
    current_start = -1
    current_len = 0

    for i in range(n):
        if not spend_on[i]:
            if current_len == 0:
                current_start = i
            current_len += 1
            if current_len > best_len:
                best_len = current_len
                best_start = current_start
        else:
            current_len = 0

    if best_len >= MIN_INTERRUPTION_LENGTH_DAYS:
        streak_convs = conv[best_start : best_start + best_len]
        return BaselineResult(
            baseline_daily=float(np.mean(streak_convs)),
            method=BaselineMethod.TIMESERIES_INTERRUPTION,
            r_squared=0.0,
            ad_marginal_effect=0.0,
            n_obs=best_len,
            warnings=[f"Time-series interruption detected: {best_len}-day spend-off streak used"],
        )

    return _result_none(warnings=["No qualifying time-series interruption found"])


def _detect_spend_drop(daily: pd.DataFrame) -> Optional[BaselineResult]:
    """Detect a ≥ 70% sustained spend drop lasting ≥ 7 days.

    When found, computes average conversions during the drop period.
    Returns None if no qualifying drop is found.
    """
    spend = daily["spend"].values
    conv = daily["actual_conversions"].values
    n = len(spend)

    # Compute rolling 7-day average spend to smooth daily noise
    roll_spend = pd.Series(spend).rolling(window=7, min_periods=7).mean().values

    best_start = -1
    best_len = 0
    current_start = -1
    current_len = 0

    threshold = INTERRUPTION_SPEND_DROP_FRAC  # 0.70

    for i in range(n):
        # Check if we're in a drop: current spend < 30% of rolling baseline
        if roll_spend[i] is not None and not np.isnan(roll_spend[i]):
            in_drop = (spend[i] / roll_spend[i]) < (1.0 - threshold) if roll_spend[i] > 0 else False
        else:
            in_drop = False

        if in_drop:
            if current_len == 0:
                current_start = i
            current_len += 1
            if current_len > best_len:
                best_len = current_len
                best_start = current_start
        else:
            current_len = 0

    if best_len >= MIN_INTERRUPTION_LENGTH_DAYS:
        streak_convs = conv[best_start : best_start + best_len]
        return BaselineResult(
            baseline_daily=float(np.mean(streak_convs)),
            method=BaselineMethod.TIMESERIES_INTERRUPTION,
            r_squared=0.0,
            ad_marginal_effect=0.0,
            n_obs=best_len,
            warnings=[f"Spend drop ≥ {threshold*100:.0f}% detected: {best_len}-day period used for baseline"],
        )

    return None


# ---------------------------------------------------------------------------
# Method 3 — Warning mode fallback
# ---------------------------------------------------------------------------

def _warning_mode_fallback(daily: pd.DataFrame) -> BaselineResult:
    """Warning mode: data < 60 days.

    Attempts the legacy spend-off average. Warns that result is approximate.
    Returns NONE if no spend-off days are available.
    """
    spend_on = daily.get("spend_on", daily["spend"] >= 5.0)
    off_convs = daily.loc[~spend_on, "actual_conversions"]

    warnings = [f"Warning mode: data < {MIN_DAYS_REGRESSION} days, result may be unreliable"]

    if off_convs.empty or off_convs.isna().all():
        return BaselineResult(
            baseline_daily=0.0,
            method=BaselineMethod.WARNING_MODE,
            r_squared=0.0,
            ad_marginal_effect=0.0,
            n_obs=len(daily),
            warnings=warnings + ["No spend-off days available for fallback baseline"],
        )

    return BaselineResult(
        baseline_daily=float(off_convs.mean()),
        method=BaselineMethod.WARNING_MODE,
        r_squared=0.0,
        ad_marginal_effect=0.0,
        n_obs=len(daily),
        warnings=warnings,
    )


# ---------------------------------------------------------------------------
# Utility
# ---------------------------------------------------------------------------

def _result_none(warnings: list[str] | None = None) -> BaselineResult:
    return BaselineResult(
        baseline_daily=0.0,
        method=BaselineMethod.NONE,
        warnings=warnings or [],
    )
