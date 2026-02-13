"""Reported vs true incremental ROAS."""

from __future__ import annotations

import pandas as pd

from ad_audit.engine.models import AuditConfig, IncrementalROASResult


def compute_incremental_roas(
    daily: pd.DataFrame,
    organic_baseline: float,
    config: AuditConfig,
) -> IncrementalROASResult:
    """Compute reported ROAS versus true incremental ROAS.

    True incremental revenue = total spend-on revenue minus the organic
    baseline revenue that would have happened anyway.

    Parameters
    ----------
    daily : merged daily DataFrame.
    organic_baseline : avg daily conversions during spend-off (from aggregate_audit).
    config : audit configuration.
    """
    total_spend = float(daily["spend"].sum())
    reported_revenue = float(daily["reported_revenue"].sum())
    actual_revenue_on = float(daily.loc[daily["spend_on"], "actual_revenue"].sum())

    spend_on_days = int(daily["spend_on"].sum())

    # Organic baseline revenue estimate: baseline conv rate * avg revenue per conversion * days
    if daily["actual_conversions"].sum() > 0:
        avg_rev_per_conv = (
            daily["actual_revenue"].sum() / daily["actual_conversions"].sum()
        )
    else:
        avg_rev_per_conv = 0.0

    organic_revenue = organic_baseline * avg_rev_per_conv * spend_on_days
    incremental_revenue = max(0.0, actual_revenue_on - organic_revenue)

    reported_roas = reported_revenue / total_spend if total_spend > 0 else 0.0
    true_roas = incremental_revenue / total_spend if total_spend > 0 else 0.0
    inflation = (
        (reported_roas - true_roas) / reported_roas if reported_roas > 0 else 0.0
    )

    return IncrementalROASResult(
        reported_roas=round(reported_roas, 4),
        true_incremental_roas=round(true_roas, 4),
        inflation_rate=round(max(0.0, inflation), 4),
        total_spend=round(total_spend, 2),
        reported_revenue=round(reported_revenue, 2),
        incremental_revenue=round(incremental_revenue, 2),
    )
