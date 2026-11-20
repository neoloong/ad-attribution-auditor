"""Period-over-period comparison with root-cause attribution."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

import pandas as pd

from ad_audit.engine.models import AuditConfig, AuditMode
from ad_audit.engine.aggregate_audit import run_aggregate_audit


@dataclass
class MetricDelta:
    """Change in a single metric between two periods."""

    metric: str
    label: str
    period_1_value: float
    period_2_value: float
    absolute_change: float
    percent_change: float | None  # None when period_1 is zero

    @property
    def direction(self) -> str:
        if self.absolute_change > 0.001:
            return "increased"
        elif self.absolute_change < -0.001:
            return "decreased"
        return "unchanged"


@dataclass
class PeriodComparisonResult:
    """Full comparison between two time periods."""

    period_1_label: str
    period_2_label: str
    deltas: list[MetricDelta] = field(default_factory=list)
    root_causes: list[str] = field(default_factory=list)


def compare_periods(
    ad_df: pd.DataFrame,
    shopify_df: pd.DataFrame,
    split_date: date | str,
    gsc_df: pd.DataFrame | None = None,
    config: AuditConfig | None = None,
) -> PeriodComparisonResult:
    """Split data at *split_date* and compare the two resulting audit periods.

    Parameters
    ----------
    ad_df : concatenated ad platform DataFrame with ``date`` column.
    shopify_df : Shopify orders with ``date`` column.
    split_date : dividing date — period 1 is before, period 2 is on or after.
    gsc_df : optional GSC data.
    config : audit config (shared for both periods).
    """
    split = pd.Timestamp(split_date)

    # Split each DataFrame
    ad_1 = ad_df[ad_df["date"] < split]
    ad_2 = ad_df[ad_df["date"] >= split]
    shop_1 = shopify_df[shopify_df["date"] < split]
    shop_2 = shopify_df[shopify_df["date"] >= split]

    gsc_1: pd.DataFrame | None = None
    gsc_2: pd.DataFrame | None = None
    if gsc_df is not None and not gsc_df.empty:
        gsc_1 = gsc_df[gsc_df["date"] < split]
        gsc_2 = gsc_df[gsc_df["date"] >= split]
        if gsc_1.empty:
            gsc_1 = None
        if gsc_2.empty:
            gsc_2 = None

    if config is None:
        config = AuditConfig(mode=AuditMode.AGGREGATE)

    # Run both audits
    r1 = run_aggregate_audit(ad_1, shop_1, gsc_1, config)
    r2 = run_aggregate_audit(ad_2, shop_2, gsc_2, config)

    # Compute deltas
    metrics = [
        ("reported_roas", "Reported ROAS",
         r1.incremental_roas.reported_roas, r2.incremental_roas.reported_roas),
        ("true_incremental_roas", "True Incremental ROAS",
         r1.incremental_roas.true_incremental_roas, r2.incremental_roas.true_incremental_roas),
        ("inflation_rate", "ROAS Inflation Rate",
         r1.incremental_roas.inflation_rate, r2.incremental_roas.inflation_rate),
        ("duplication_rate", "Duplication Rate",
         r1.deduplication.duplication_rate, r2.deduplication.duplication_rate),
        ("cannibalization_score", "Cannibalization Score",
         r1.cannibalization.cannibalization_score, r2.cannibalization.cannibalization_score),
        ("total_spend", "Total Ad Spend",
         r1.incremental_roas.total_spend, r2.incremental_roas.total_spend),
        ("organic_baseline", "Organic Baseline (conv/day)",
         r1.organic_baseline_conversions, r2.organic_baseline_conversions),
        ("correlation_mean", "Spend-Conversion Correlation",
         r1.correlation_mean, r2.correlation_mean),
    ]

    deltas: list[MetricDelta] = []
    for metric, label, v1, v2 in metrics:
        abs_change = v2 - v1
        pct = ((v2 - v1) / v1) if v1 != 0 else None
        deltas.append(MetricDelta(
            metric=metric,
            label=label,
            period_1_value=round(v1, 4),
            period_2_value=round(v2, 4),
            absolute_change=round(abs_change, 4),
            percent_change=round(pct, 4) if pct is not None else None,
        ))

    # Root cause attribution
    root_causes = _attribute_root_causes(deltas, r1, r2)

    # Build labels
    p1_dates = ad_1["date"]
    p2_dates = ad_2["date"]
    p1_label = f"{p1_dates.min().date()} to {p1_dates.max().date()}" if not p1_dates.empty else "Period 1 (no data)"
    p2_label = f"{p2_dates.min().date()} to {p2_dates.max().date()}" if not p2_dates.empty else "Period 2 (no data)"

    return PeriodComparisonResult(
        period_1_label=p1_label,
        period_2_label=p2_label,
        deltas=deltas,
        root_causes=root_causes,
    )


def _attribute_root_causes(
    deltas: list[MetricDelta],
    r1,
    r2,
) -> list[str]:
    """Generate plain-English root cause explanations for key changes."""
    causes: list[str] = []
    delta_map = {d.metric: d for d in deltas}

    # True ROAS changed
    roas_d = delta_map.get("true_incremental_roas")
    if roas_d and abs(roas_d.absolute_change) > 0.05:
        direction = "improved" if roas_d.absolute_change > 0 else "declined"
        causes.append(
            f"True incremental ROAS {direction} from "
            f"{roas_d.period_1_value:.2f}x to {roas_d.period_2_value:.2f}x."
        )

        # Why? Check contributing factors
        dup_d = delta_map.get("duplication_rate")
        if dup_d and abs(dup_d.absolute_change) > 0.03:
            dup_dir = "increased" if dup_d.absolute_change > 0 else "decreased"
            causes.append(
                f"  - Duplication rate {dup_dir} from "
                f"{dup_d.period_1_value:.1%} to {dup_d.period_2_value:.1%} "
                f"(platforms {'over-counted more' if dup_d.absolute_change > 0 else 'became more accurate'})."
            )

        cannibal_d = delta_map.get("cannibalization_score")
        if cannibal_d and abs(cannibal_d.absolute_change) > 0.03:
            can_dir = "increased" if cannibal_d.absolute_change > 0 else "decreased"
            causes.append(
                f"  - Cannibalization {can_dir} from "
                f"{cannibal_d.period_1_value:.1%} to {cannibal_d.period_2_value:.1%} "
                f"({'more' if cannibal_d.absolute_change > 0 else 'fewer'} organic users "
                f"claimed by ad platforms)."
            )

        baseline_d = delta_map.get("organic_baseline")
        if baseline_d and abs(baseline_d.absolute_change) > 0.5:
            base_dir = "rose" if baseline_d.absolute_change > 0 else "fell"
            causes.append(
                f"  - Organic baseline {base_dir} from "
                f"{baseline_d.period_1_value:.1f} to {baseline_d.period_2_value:.1f} "
                f"conv/day (brand is {'growing' if baseline_d.absolute_change > 0 else 'shrinking'} organically)."
            )

        spend_d = delta_map.get("total_spend")
        if spend_d and spend_d.percent_change is not None and abs(spend_d.percent_change) > 0.1:
            spend_dir = "increased" if spend_d.absolute_change > 0 else "decreased"
            causes.append(
                f"  - Total ad spend {spend_dir} by "
                f"{abs(spend_d.percent_change):.0%} "
                f"(${spend_d.period_1_value:,.0f} → ${spend_d.period_2_value:,.0f})."
            )

    # Correlation changed
    corr_d = delta_map.get("correlation_mean")
    if corr_d and abs(corr_d.absolute_change) > 0.1:
        corr_dir = "strengthened" if corr_d.absolute_change > 0 else "weakened"
        causes.append(
            f"Spend-conversion correlation {corr_dir} "
            f"({corr_d.period_1_value:.2f} → {corr_d.period_2_value:.2f}), "
            f"suggesting ad spend is {'more' if corr_d.absolute_change > 0 else 'less'} "
            f"effective at driving actual sales."
        )

    if not causes:
        causes.append("No significant changes detected between the two periods.")

    return causes
