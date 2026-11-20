"""Health check alerts: configurable threshold-based warnings on audit results."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from ad_audit.engine.models import AuditResult


class Severity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class HealthCheckAlert:
    """A single alert produced by a health check."""

    severity: Severity
    title: str
    message: str
    metric: str
    value: float
    threshold: float


@dataclass
class HealthCheckThresholds:
    """Configurable thresholds for health checks."""

    duplication_rate_warning: float = 0.15
    duplication_rate_critical: float = 0.30
    cannibalization_score_warning: float = 0.20
    cannibalization_score_critical: float = 0.40
    inflation_rate_warning: float = 0.30
    inflation_rate_critical: float = 0.60
    correlation_low_warning: float = 0.3
    correlation_negative_critical: float = 0.0
    organic_baseline_min: float = 0.5


def run_health_checks(
    result: AuditResult,
    thresholds: HealthCheckThresholds | None = None,
) -> list[HealthCheckAlert]:
    """Evaluate an AuditResult against thresholds and return alerts.

    Returns a list of alerts sorted by severity (critical first).
    """
    if thresholds is None:
        thresholds = HealthCheckThresholds()

    alerts: list[HealthCheckAlert] = []

    # --- Duplication Rate ---
    dup_rate = result.deduplication.duplication_rate
    if dup_rate >= thresholds.duplication_rate_critical:
        alerts.append(HealthCheckAlert(
            severity=Severity.CRITICAL,
            title="High Duplication Rate",
            message=(
                f"Ad platforms are over-reporting conversions by {dup_rate:.0%}. "
                f"More than {thresholds.duplication_rate_critical:.0%} of reported "
                f"conversions have no matching e-commerce order."
            ),
            metric="duplication_rate",
            value=dup_rate,
            threshold=thresholds.duplication_rate_critical,
        ))
    elif dup_rate >= thresholds.duplication_rate_warning:
        alerts.append(HealthCheckAlert(
            severity=Severity.WARNING,
            title="Elevated Duplication Rate",
            message=(
                f"Duplication rate is {dup_rate:.0%} — ad platforms may be "
                f"over-counting conversions."
            ),
            metric="duplication_rate",
            value=dup_rate,
            threshold=thresholds.duplication_rate_warning,
        ))

    # --- ROAS Inflation ---
    inflation = result.incremental_roas.inflation_rate
    if inflation >= thresholds.inflation_rate_critical:
        alerts.append(HealthCheckAlert(
            severity=Severity.CRITICAL,
            title="Severe ROAS Inflation",
            message=(
                f"Reported ROAS ({result.incremental_roas.reported_roas:.2f}x) is "
                f"inflated by {inflation:.0%} versus true incremental ROAS "
                f"({result.incremental_roas.true_incremental_roas:.2f}x). "
                f"Ad spend may not be generating real returns."
            ),
            metric="inflation_rate",
            value=inflation,
            threshold=thresholds.inflation_rate_critical,
        ))
    elif inflation >= thresholds.inflation_rate_warning:
        alerts.append(HealthCheckAlert(
            severity=Severity.WARNING,
            title="ROAS Inflation Detected",
            message=(
                f"Reported ROAS is inflated by {inflation:.0%}. True incremental ROAS "
                f"is {result.incremental_roas.true_incremental_roas:.2f}x."
            ),
            metric="inflation_rate",
            value=inflation,
            threshold=thresholds.inflation_rate_warning,
        ))

    # --- Cannibalization Score ---
    cannibal = result.cannibalization.cannibalization_score
    if cannibal >= thresholds.cannibalization_score_critical:
        alerts.append(HealthCheckAlert(
            severity=Severity.CRITICAL,
            title="High Cannibalization",
            message=(
                f"Cannibalization score is {cannibal:.0%} — on {cannibal:.0%} of "
                f"spend-on days, ad platform claims overlap with organic brand search. "
                f"A large share of 'conversions' may be users who would have purchased anyway."
            ),
            metric="cannibalization_score",
            value=cannibal,
            threshold=thresholds.cannibalization_score_critical,
        ))
    elif cannibal >= thresholds.cannibalization_score_warning:
        alerts.append(HealthCheckAlert(
            severity=Severity.WARNING,
            title="Elevated Cannibalization",
            message=(
                f"Cannibalization score is {cannibal:.0%} — ad platforms may be "
                f"claiming credit for organic purchases."
            ),
            metric="cannibalization_score",
            value=cannibal,
            threshold=thresholds.cannibalization_score_warning,
        ))

    # --- Spend-Conversion Correlation ---
    corr = result.correlation_mean
    if corr <= thresholds.correlation_negative_critical:
        alerts.append(HealthCheckAlert(
            severity=Severity.CRITICAL,
            title="Negative Spend-Conversion Correlation",
            message=(
                f"Spend and conversions are negatively correlated ({corr:.2f}). "
                f"Increasing ad spend may not be driving more actual sales."
            ),
            metric="correlation_mean",
            value=corr,
            threshold=thresholds.correlation_negative_critical,
        ))
    elif corr <= thresholds.correlation_low_warning:
        alerts.append(HealthCheckAlert(
            severity=Severity.WARNING,
            title="Weak Spend-Conversion Correlation",
            message=(
                f"Spend-conversion correlation is only {corr:.2f}. "
                f"Ad spend has a weak relationship with actual sales."
            ),
            metric="correlation_mean",
            value=corr,
            threshold=thresholds.correlation_low_warning,
        ))

    # --- Organic Baseline ---
    baseline = result.organic_baseline_conversions
    if 0 < baseline < thresholds.organic_baseline_min:
        alerts.append(HealthCheckAlert(
            severity=Severity.INFO,
            title="Low Organic Baseline",
            message=(
                f"Organic baseline is only {baseline:.1f} conversions/day. "
                f"This may indicate limited spend-off data for reliable estimation."
            ),
            metric="organic_baseline_conversions",
            value=baseline,
            threshold=thresholds.organic_baseline_min,
        ))

    # --- No GSC data (cannibalization can't be measured) ---
    if (result.daily_df is not None
            and "brand_clicks" not in result.daily_df.columns):
        alerts.append(HealthCheckAlert(
            severity=Severity.INFO,
            title="No Brand Search Data",
            message=(
                "GSC brand search data was not provided. Cannibalization scoring "
                "is disabled. Upload GSC data for a more complete audit."
            ),
            metric="gsc_data",
            value=0,
            threshold=0,
        ))

    # Sort: critical first, then warning, then info
    severity_order = {Severity.CRITICAL: 0, Severity.WARNING: 1, Severity.INFO: 2}
    alerts.sort(key=lambda a: severity_order[a.severity])

    return alerts
