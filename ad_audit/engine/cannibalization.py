"""Brand-search cannibalization scoring."""

from __future__ import annotations

import numpy as np
import pandas as pd

from ad_audit.engine.models import AuditConfig, CannibalizationResult


def compute_cannibalization(
    daily: pd.DataFrame,
    config: AuditConfig,
) -> CannibalizationResult:
    """Score days where ad platform claims overlap with elevated brand search.

    A day is flagged as "cannibalized" when **both** the platform-reported
    conversions and brand-search clicks exceed their respective rolling
    averages — meaning the ad platform is likely claiming credit for users
    who were already searching for the brand organically.

    Parameters
    ----------
    daily : merged daily DataFrame with columns ``reported_conversions``,
            ``brand_clicks``, ``spend``, ``actual_revenue``.
    config : audit configuration (rolling_avg_days).
    """
    if daily.empty or "brand_clicks" not in daily.columns:
        return CannibalizationResult()

    df = daily.copy()
    window = config.rolling_avg_days

    df["meta_rolling_avg"] = (
        df["reported_conversions"].rolling(window, min_periods=1).mean()
    )
    df["brand_rolling_avg"] = (
        df["brand_clicks"].rolling(window, min_periods=1).mean()
    )

    # Flag days where both exceed their rolling averages
    df["cannibalized"] = (
        (df["reported_conversions"] > df["meta_rolling_avg"])
        & (df["brand_clicks"] > df["brand_rolling_avg"])
        & df["spend_on"]
    )

    total_spend_on_days = int(df["spend_on"].sum())
    cannibalized_days = int(df["cannibalized"].sum())

    # Revenue fraction: share of spend-on revenue that falls on cannibalized days
    spend_on_revenue = df.loc[df["spend_on"], "actual_revenue"].sum()
    cannibalized_revenue = df.loc[df["cannibalized"], "actual_revenue"].sum()
    rev_fraction = (
        cannibalized_revenue / spend_on_revenue if spend_on_revenue > 0 else 0.0
    )

    score = cannibalized_days / total_spend_on_days if total_spend_on_days > 0 else 0.0

    return CannibalizationResult(
        cannibalized_days=cannibalized_days,
        total_days=total_spend_on_days,
        cannibalization_score=round(score, 4),
        cannibalized_revenue_fraction=round(rev_fraction, 4),
    )
