export interface DeduplicationResult {
  platformReportedConversions: number;
  actualConversions: number;
  overlapCount: number;
  duplicationRate: number;
}

export interface CannibalizationResult {
  cannibalizedDays: number;
  totalDays: number;
  cannibalizationScore: number;
  cannibalizedRevenueFraction: number;
}

export interface IncrementalROASResult {
  reportedROAS: number;
  trueIncrementalROAS: number;
  inflationRate: number;
  totalSpend: number;
  reportedRevenue: number;
  incrementalRevenue: number;
}

export interface AuditConfig {
  attributionWindowDays: number;
  cannibalizationLookbackHours: number;
  spendOnThreshold: number;
  correlationWindowDays: number;
  rollingAvgDays: number;
}

export const DEFAULT_CONFIG: AuditConfig = {
  attributionWindowDays: 7,
  cannibalizationLookbackHours: 24,
  spendOnThreshold: 5,
  correlationWindowDays: 7,
  rollingAvgDays: 30,
};

export interface DailyRow {
  date: string;
  spend: number;
  reportedConversions: number;
  reportedRevenue: number;
  actualConversions: number;
  actualRevenue: number;
  brandClicks: number;
  brandImpressions: number;
  spendOn: boolean;
  metaRollingAvg?: number;
  brandRollingAvg?: number;
  cannibalized?: boolean;
}

export interface AuditResult {
  config: AuditConfig;
  deduplication: DeduplicationResult;
  cannibalization: CannibalizationResult;
  incrementalROAS: IncrementalROASResult;
  correlationMean: number;
  organicBaselineConversions: number;
  incrementalConversionsPerDay: number;
  dailyRows: DailyRow[];
  hasGSC: boolean;
}

export type Severity = "critical" | "warning" | "info";

export interface HealthCheckAlert {
  severity: Severity;
  title: string;
  message: string;
  metric: string;
  value: number;
  threshold: number;
}

export interface HealthCheckThresholds {
  duplicationRateWarning: number;
  duplicationRateCritical: number;
  cannibalizationScoreWarning: number;
  cannibalizationScoreCritical: number;
  inflationRateWarning: number;
  inflationRateCritical: number;
  correlationLowWarning: number;
  correlationNegativeCritical: number;
  organicBaselineMin: number;
}

export const DEFAULT_THRESHOLDS: HealthCheckThresholds = {
  duplicationRateWarning: 0.15,
  duplicationRateCritical: 0.3,
  cannibalizationScoreWarning: 0.2,
  cannibalizationScoreCritical: 0.4,
  inflationRateWarning: 0.3,
  inflationRateCritical: 0.6,
  correlationLowWarning: 0.3,
  correlationNegativeCritical: 0,
  organicBaselineMin: 0.5,
};
