import type { AuditResult, HealthCheckAlert, HealthCheckThresholds } from "./types";
import { DEFAULT_THRESHOLDS } from "./types";

export function runHealthChecks(
  result: AuditResult,
  thresholds: HealthCheckThresholds = DEFAULT_THRESHOLDS,
): HealthCheckAlert[] {
  const alerts: HealthCheckAlert[] = [];

  // Duplication Rate
  const dupRate = result.deduplication.duplicationRate;
  if (dupRate >= thresholds.duplicationRateCritical) {
    alerts.push({
      severity: "critical",
      title: "High Duplication Rate",
      message: `Ad platforms are over-reporting conversions by ${(dupRate * 100).toFixed(0)}%. More than ${(thresholds.duplicationRateCritical * 100).toFixed(0)}% of reported conversions have no matching e-commerce order.`,
      metric: "duplicationRate",
      value: dupRate,
      threshold: thresholds.duplicationRateCritical,
    });
  } else if (dupRate >= thresholds.duplicationRateWarning) {
    alerts.push({
      severity: "warning",
      title: "Elevated Duplication Rate",
      message: `Duplication rate is ${(dupRate * 100).toFixed(0)}% — ad platforms may be over-counting conversions.`,
      metric: "duplicationRate",
      value: dupRate,
      threshold: thresholds.duplicationRateWarning,
    });
  }

  // ROAS Inflation
  const inflation = result.incrementalROAS.inflationRate;
  if (inflation >= thresholds.inflationRateCritical) {
    alerts.push({
      severity: "critical",
      title: "Severe ROAS Inflation",
      message: `Reported ROAS (${result.incrementalROAS.reportedROAS.toFixed(2)}x) is inflated by ${(inflation * 100).toFixed(0)}% versus true incremental ROAS (${result.incrementalROAS.trueIncrementalROAS.toFixed(2)}x). Ad spend may not be generating real returns.`,
      metric: "inflationRate",
      value: inflation,
      threshold: thresholds.inflationRateCritical,
    });
  } else if (inflation >= thresholds.inflationRateWarning) {
    alerts.push({
      severity: "warning",
      title: "ROAS Inflation Detected",
      message: `Reported ROAS is inflated by ${(inflation * 100).toFixed(0)}%. True incremental ROAS is ${result.incrementalROAS.trueIncrementalROAS.toFixed(2)}x.`,
      metric: "inflationRate",
      value: inflation,
      threshold: thresholds.inflationRateWarning,
    });
  }

  // Cannibalization Score
  const cannibal = result.cannibalization.cannibalizationScore;
  if (cannibal >= thresholds.cannibalizationScoreCritical) {
    alerts.push({
      severity: "critical",
      title: "High Cannibalization",
      message: `Cannibalization score is ${(cannibal * 100).toFixed(0)}% — on ${(cannibal * 100).toFixed(0)}% of spend-on days, ad platform claims overlap with organic brand search. A large share of 'conversions' may be users who would have purchased anyway.`,
      metric: "cannibalizationScore",
      value: cannibal,
      threshold: thresholds.cannibalizationScoreCritical,
    });
  } else if (cannibal >= thresholds.cannibalizationScoreWarning) {
    alerts.push({
      severity: "warning",
      title: "Elevated Cannibalization",
      message: `Cannibalization score is ${(cannibal * 100).toFixed(0)}% — ad platforms may be claiming credit for organic purchases.`,
      metric: "cannibalizationScore",
      value: cannibal,
      threshold: thresholds.cannibalizationScoreWarning,
    });
  }

  // Spend-Conversion Correlation
  const corr = result.correlationMean;
  if (corr <= thresholds.correlationNegativeCritical) {
    alerts.push({
      severity: "critical",
      title: "Negative Spend-Conversion Correlation",
      message: `Spend and conversions are negatively correlated (${corr.toFixed(2)}). Increasing ad spend may not be driving more actual sales.`,
      metric: "correlationMean",
      value: corr,
      threshold: thresholds.correlationNegativeCritical,
    });
  } else if (corr <= thresholds.correlationLowWarning) {
    alerts.push({
      severity: "warning",
      title: "Weak Spend-Conversion Correlation",
      message: `Spend-conversion correlation is only ${corr.toFixed(2)}. Ad spend has a weak relationship with actual sales.`,
      metric: "correlationMean",
      value: corr,
      threshold: thresholds.correlationLowWarning,
    });
  }

  // Organic Baseline
  const baseline = result.organicBaselineConversions;
  if (baseline > 0 && baseline < thresholds.organicBaselineMin) {
    alerts.push({
      severity: "info",
      title: "Low Organic Baseline",
      message: `Organic baseline is only ${baseline.toFixed(1)} conversions/day. This may indicate limited spend-off data for reliable estimation.`,
      metric: "organicBaselineConversions",
      value: baseline,
      threshold: thresholds.organicBaselineMin,
    });
  }

  // No GSC data
  if (!result.hasGSC) {
    alerts.push({
      severity: "info",
      title: "No Brand Search Data",
      message: "GSC brand search data was not provided. Cannibalization scoring is disabled. Upload GSC data for a more complete audit.",
      metric: "gscData",
      value: 0,
      threshold: 0,
    });
  }

  const severityOrder = { critical: 0, warning: 1, info: 2 };
  alerts.sort((a, b) => severityOrder[a.severity] - severityOrder[b.severity]);

  return alerts;
}
