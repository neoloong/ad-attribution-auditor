"""Aggregate audit: time-series approach using daily metrics."""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.stats import pearsonr

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
    """Average daily Shopify conversions during spend-off periods."""
    off = daily.loc[~daily["spend_on"], "actual_conversions"]
    if off.empty:
        return 0.0
    return float(off.mean())


def _incremental_per_day(daily: pd.DataFrame, organic_baseline: float) -> float:
    """Average daily incremental conversions = spend-on avg minus organic baseline."""
    on = daily.loc[daily["spend_on"], "actual_conversions"]
    if on.empty:
        return 0.0
    return max(0.0, float(on.mean()) - organic_baseline)


def _rolling_correlation(daily: pd.DataFrame, window: int) -> float:
    """Mean of rolling Pearson r between spend and actual_conversions."""
    if len(daily) < window:
        if len(daily) >= 3:
            r, _ = pearsonr(daily["spend"], daily["actual_conversions"])
            return float(r) if np.isfinite(r) else 0.0
        return 0.0

    rs = []
    spend = daily["spend"].values
    conv = daily["actual_conversions"].values
    for i in range(len(daily) - window + 1):
        s = spend[i : i + window]
        c = conv[i : i + window]
        if s.std() > 0 and c.std() > 0:
            r, _ = pearsonr(s, c)
            if np.isfinite(r):
                rs.append(r)
    return float(np.mean(rs)) if rs else 0.0
