"""Aggregate audit: time-series approach using daily metrics."""

from __future__ import annotations

import numpy as np
import pandas as pd

from ad_audit.engine.models import AuditConfig, AuditMode, AuditResult
from ad_audit.engine.deduplication import compute_deduplication
from ad_audit.engine.cannibalization import compute_cannibalization
from ad_audit.engine.incremental_roas import compute_incremental_roas


def run_aggregate_audit(
    ad_df: pd.DataFrame,
    shopify_df: pd.DataFrame,
    gsc_df: pd.DataFrame | None = None,
    config: AuditConfig | None = None,
) -> AuditResult:
    """Execute the full aggregate audit pipeline.

    Parameters
    ----------
    ad_df : pre-concatenated ad platform DataFrame (columns: date, spend,
        reported_conversions, reported_revenue, platform).  May contain rows
        from Meta, Google Ads, or both.
    shopify_df : normalized Shopify/e-commerce orders DataFrame (columns: date, revenue, ...)
    gsc_df : normalized GSC DataFrame (columns: date, clicks, impressions).
        Optional — cannibalization scoring is skipped when *None* or empty.
    config : audit configuration; defaults used if *None*
    """
    if config is None:
        config = AuditConfig(mode=AuditMode.AGGREGATE)

    daily = _build_daily_merged(ad_df, shopify_df, gsc_df)

    # Spend on/off classification
    daily["spend_on"] = daily["spend"] >= config.spend_on_threshold

    # Organic baseline & incremental conversions
    organic_baseline = _organic_baseline(daily)
    incremental_per_day = _incremental_per_day(daily, organic_baseline)

    # Rolling Pearson correlation
    corr_mean = _rolling_correlation(daily, config.correlation_window_days)

    # Sub-analyses
    dedup = compute_deduplication(daily)
    cannibal = compute_cannibalization(daily, config)
    iroas = compute_incremental_roas(daily, organic_baseline, config)

    return AuditResult(
        mode=AuditMode.AGGREGATE,
        config=config,
        deduplication=dedup,
        cannibalization=cannibal,
        incremental_roas=iroas,
        correlation_mean=corr_mean,
        organic_baseline_conversions=organic_baseline,
        incremental_conversions_per_day=incremental_per_day,
        daily_df=daily,
    )


# ---- internal helpers ----

def _build_daily_merged(
    ad_df: pd.DataFrame,
    shopify_df: pd.DataFrame,
    gsc_df: pd.DataFrame | None,
) -> pd.DataFrame:
    """Merge ad platform + Shopify (+ optional GSC) into a single daily DataFrame."""
    # Ad platform daily aggregation (works for any combination of platforms)
    ad_daily = (
        ad_df.groupby("date")
        .agg(
            spend=("spend", "sum"),
            reported_conversions=("reported_conversions", "sum"),
            reported_revenue=("reported_revenue", "sum"),
        )
        .reset_index()
    )

    # Shopify daily aggregation
    shopify_daily = (
        shopify_df.groupby("date")
        .agg(
            actual_conversions=("revenue", "count"),
            actual_revenue=("revenue", "sum"),
        )
        .reset_index()
    )

    # Outer merge so we keep all dates
    daily = ad_daily.merge(shopify_daily, on="date", how="outer")

    # GSC daily aggregation (optional)
    if gsc_df is not None and not gsc_df.empty:
        gsc_daily = (
            gsc_df.groupby("date")
            .agg(brand_clicks=("clicks", "sum"), brand_impressions=("impressions", "sum"))
            .reset_index()
        )
        daily = daily.merge(gsc_daily, on="date", how="outer")

    daily = daily.sort_values("date").reset_index(drop=True)

    # Fill NaN with 0 for numeric columns
    num_cols = daily.select_dtypes(include="number").columns
    daily[num_cols] = daily[num_cols].fillna(0)

    return daily


def _organic_baseline(daily: pd.DataFrame) -> float:
    """Estimate organic (non-ad) daily conversions.

    Decision tree:
    1. Regression-based (OLS): regress actual_conversions ~ spend.
       Intercept = organic baseline when spend = 0.
    2. Fallback: time-series interruption detection
       (clear spend drop ≥ 7 consecutive days).
    3. Spend-off day average (legacy fallback).
    4. Zero if no data.

    Returns
    -------
    float : estimated avg daily organic conversions.
    """
    # --- Method 1: OLS regression (requires ≥ 60 days) ---
    baseline, method, r2 = _regression_baseline(daily)
    if method is not None:
        return max(0.0, baseline)

    # --- Method 2: Time-series interruption ---
    baseline = _timeseries_interruption_baseline(daily)
    if baseline is not None:
        return max(0.0, baseline)

    # --- Method 3: Legacy spend-off day average ---
    off = daily.loc[~daily["spend_on"], "actual_conversions"]
    if not off.empty and not off.isna().all():
        return float(off.mean())

    return 0.0


def _regression_baseline(daily: pd.DataFrame) -> tuple[float, str | None, float]:
    """OLS regression: actual_conversions ~ spend.

    Requires:
    - ≥ 60 days of data
    - Spend variation: non-zero std and some zero-spend days
    - Statistically significant, positively-sloped model

    Returns
    -------
    (intercept, method_label, r2)  — method_label is None if conditions not met.
    """
    MIN_DAYS = 60
    if len(daily) < MIN_DAYS:
        return 0.0, None, 0.0

    spend = daily["spend"].values
    conv = daily["actual_conversions"].values

    # Need spend variation and some zero-spend days for reliable intercept
    if spend.std() < 1.0:
        return 0.0, None, 0.0

    zero_spend_days = np.sum(spend == 0)
    if zero_spend_days < 3:
        return 0.0, None, 0.0

    # OLS using normal equations (no external dependency beyond numpy)
    n = len(spend)
    X = np.column_stack([np.ones(n), spend])
    try:
        # Solve X^T X beta = X^T y
        XtX = X.T @ X
        Xty = X.T @ conv
        beta = np.linalg.solve(XtX, Xty)
    except np.linalg.LinAlgError:
        return 0.0, None, 0.0

    intercept, slope = beta[0], beta[1]

    # Intercept must be non-negative (organic baseline can't be negative)
    # Slope should be positive (more spend → more conversions)
    if intercept < 0:
        return 0.0, None, 0.0

    # R² check — require modest fit
    y_hat = X @ beta
    ss_res = np.sum((conv - y_hat) ** 2)
    ss_tot = np.sum((conv - conv.mean()) ** 2)
    r2 = 1.0 - (ss_res / ss_tot) if ss_tot > 0 else 0.0

    if r2 < 0.01:  # Nearly flat model — intercept ≈ mean, not informative
        return 0.0, None, 0.0

    return float(intercept), "regression", float(r2)


def _timeseries_interruption_baseline(daily: pd.DataFrame) -> float | None:
    """Time-series interruption detection for organic baseline.

    Looks for a clear, sustained spend drop (spend_on=False) lasting ≥ 7
    consecutive days. Computes the average conversions during those periods.

    Returns None if no qualifying interruption is found.
    """
    MIN_INTERRUPTION_DAYS = 7

    spend_on = daily["spend_on"].values
    conv = daily["actual_conversions"].values
    n = len(spend_on)

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

    if best_len >= MIN_INTERRUPTION_DAYS:
        streak_convs = conv[best_start : best_start + best_len]
        return float(streak_convs.mean())

    return None


def _incremental_per_day(daily: pd.DataFrame, organic_baseline: float) -> float:
    """Average daily incremental conversions = spend-on avg minus organic baseline."""
    on = daily.loc[daily["spend_on"], "actual_conversions"]
    if on.empty:
        return 0.0
    return max(0.0, float(on.mean()) - organic_baseline)


def _rolling_correlation(daily: pd.DataFrame, window: int) -> float:
    """Mean of rolling Pearson r between spend and actual_conversions.

    Vectorized implementation using pandas rolling + std/cov formula for Pearson r.
    """
    if len(daily) < 2:
        return 0.0

    spend = daily["spend"]
    conv = daily["actual_conversions"]

    if len(daily) < window:
        # Not enough rows for a full rolling window — use global correlation
        if spend.std() > 0 and conv.std() > 0:
            r = np.corrcoef(spend.values, conv.values)[0, 1]
            return float(r) if np.isfinite(r) else 0.0
        return 0.0

    # Vectorized rolling Pearson r:
    # r = Cov(spend, conv) / (Std(spend) * Std(conv))
    roll = daily[["spend", "actual_conversions"]].rolling(window=window)
    roll_spend_mean = roll["spend"].mean()
    roll_conv_mean = roll["actual_conversions"].mean()
    # Covariance: E[(spend - mean_spend)*(conv - mean_conv)]
    cov = (
        (daily["spend"] - roll_spend_mean)
        * (daily["actual_conversions"] - roll_conv_mean)
    ).rolling(window=window).mean()
    std_spend = roll["spend"].std()
    std_conv = roll["actual_conversions"].std()

    with np.errstate(divide="ignore", invalid="ignore"):
        rs = cov / (std_spend * std_conv)
    rs = rs.replace([np.inf, -np.inf], np.nan).dropna()
    valid_rs = rs[np.isfinite(rs)]
    return float(valid_rs.mean()) if not valid_rs.empty else 0.0
