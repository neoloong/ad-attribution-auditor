"""Tests for health check alerts."""

from ad_audit.engine.models import (
    AuditResult,
    DeduplicationResult,
    CannibalizationResult,
    IncrementalROASResult,
)
from ad_audit.engine.health_checks import (
    run_health_checks,
    HealthCheckThresholds,
    Severity,
)
import pandas as pd


def _make_result(**kwargs) -> AuditResult:
    """Build an AuditResult with specified overrides."""
    return AuditResult(
        deduplication=kwargs.get("dedup", DeduplicationResult()),
        cannibalization=kwargs.get("cannibal", CannibalizationResult()),
        incremental_roas=kwargs.get("iroas", IncrementalROASResult()),
        correlation_mean=kwargs.get("correlation", 0.5),
        organic_baseline_conversions=kwargs.get("baseline", 3.0),
        daily_df=kwargs.get("daily_df", pd.DataFrame({"brand_clicks": [1]})),
    )


def test_no_alerts_healthy_result():
    result = _make_result(
        dedup=DeduplicationResult(duplication_rate=0.05),
        iroas=IncrementalROASResult(inflation_rate=0.1, reported_roas=2.0, true_incremental_roas=1.8),
        cannibal=CannibalizationResult(cannibalization_score=0.05),
        correlation=0.7,
        baseline=5.0,
    )
    alerts = run_health_checks(result)
    assert len(alerts) == 0


def test_critical_duplication():
    result = _make_result(
        dedup=DeduplicationResult(duplication_rate=0.45),
    )
    alerts = run_health_checks(result)
    dup_alerts = [a for a in alerts if a.metric == "duplication_rate"]
    assert len(dup_alerts) == 1
    assert dup_alerts[0].severity == Severity.CRITICAL


def test_warning_duplication():
    result = _make_result(
        dedup=DeduplicationResult(duplication_rate=0.20),
    )
    alerts = run_health_checks(result)
    dup_alerts = [a for a in alerts if a.metric == "duplication_rate"]
    assert len(dup_alerts) == 1
    assert dup_alerts[0].severity == Severity.WARNING


def test_critical_inflation():
    result = _make_result(
        iroas=IncrementalROASResult(
            inflation_rate=0.70, reported_roas=5.0, true_incremental_roas=1.5
        ),
    )
    alerts = run_health_checks(result)
    infl_alerts = [a for a in alerts if a.metric == "inflation_rate"]
    assert len(infl_alerts) == 1
    assert infl_alerts[0].severity == Severity.CRITICAL


def test_negative_correlation():
    result = _make_result(correlation=-0.3)
    alerts = run_health_checks(result)
    corr_alerts = [a for a in alerts if a.metric == "correlation_mean"]
    assert len(corr_alerts) == 1
    assert corr_alerts[0].severity == Severity.CRITICAL


def test_no_gsc_info_alert():
    result = _make_result(daily_df=pd.DataFrame({"spend": [100]}))
    alerts = run_health_checks(result)
    gsc_alerts = [a for a in alerts if a.metric == "gsc_data"]
    assert len(gsc_alerts) == 1
    assert gsc_alerts[0].severity == Severity.INFO


def test_custom_thresholds():
    result = _make_result(
        dedup=DeduplicationResult(duplication_rate=0.10),
    )
    # Default: 0.10 is below warning (0.15), so no alert
    alerts = run_health_checks(result)
    dup_alerts = [a for a in alerts if a.metric == "duplication_rate"]
    assert len(dup_alerts) == 0

    # Custom: lower threshold makes it a warning
    custom = HealthCheckThresholds(duplication_rate_warning=0.08)
    alerts = run_health_checks(result, custom)
    dup_alerts = [a for a in alerts if a.metric == "duplication_rate"]
    assert len(dup_alerts) == 1


def test_alerts_sorted_by_severity():
    result = _make_result(
        dedup=DeduplicationResult(duplication_rate=0.50),  # critical
        iroas=IncrementalROASResult(inflation_rate=0.35),  # warning
        daily_df=pd.DataFrame({"spend": [100]}),  # info (no gsc)
    )
    alerts = run_health_checks(result)
    severities = [a.severity for a in alerts]
    # Critical should come first
    assert severities[0] == Severity.CRITICAL
    severity_order = {Severity.CRITICAL: 0, Severity.WARNING: 1, Severity.INFO: 2}
    for i in range(len(severities) - 1):
        assert severity_order[severities[i]] <= severity_order[severities[i + 1]]
