import { describe, it, expect } from "vitest";
import { runHealthChecks } from "../health-checks";
import type { AuditResult, HealthCheckThresholds } from "../types";
import { DEFAULT_THRESHOLDS } from "../types";

function makeResult(overrides: Partial<AuditResult>): AuditResult {
  return {
    config: { attributionWindowDays: 7, cannibalizationLookbackHours: 24, spendOnThreshold: 5, correlationWindowDays: 7, rollingAvgDays: 30 },
    deduplication: {
      platformReportedConversions: 100,
      actualConversions: 100,
      overlapCount: 100,
      duplicationRate: 0,
    },
    cannibalization: {
      cannibalizedDays: 0,
      totalDays: 0,
      cannibalizationScore: 0,
      cannibalizedRevenueFraction: 0,
    },
    incrementalROAS: {
      reportedROAS: 3.0,
      trueIncrementalROAS: 2.5,
      inflationRate: 0.1,
      totalSpend: 1000,
      reportedRevenue: 3000,
      incrementalRevenue: 2500,
    },
    correlationMean: 0.5,
    organicBaselineConversions: 3.0,
    incrementalConversionsPerDay: 2.0,
    dailyRows: [],
    hasGSC: true,
    ...overrides,
  };
}

describe("runHealthChecks", () => {
  it("returns no alerts for a healthy result", () => {
    const result = makeResult({ hasGSC: true });
    const alerts = runHealthChecks(result);
    expect(alerts).toHaveLength(0);
  });

  it("flags critical duplication rate", () => {
    const result = makeResult({
      deduplication: { platformReportedConversions: 100, actualConversions: 55, overlapCount: 55, duplicationRate: 0.45 },
    });
    const alerts = runHealthChecks(result);
    const dupAlerts = alerts.filter((a) => a.metric === "duplicationRate");
    expect(dupAlerts).toHaveLength(1);
    expect(dupAlerts[0].severity).toBe("critical");
  });

  it("flags warning duplication rate", () => {
    const result = makeResult({
      deduplication: { platformReportedConversions: 100, actualConversions: 80, overlapCount: 80, duplicationRate: 0.2 },
    });
    const alerts = runHealthChecks(result);
    const dupAlerts = alerts.filter((a) => a.metric === "duplicationRate");
    expect(dupAlerts).toHaveLength(1);
    expect(dupAlerts[0].severity).toBe("warning");
  });

  it("flags critical ROAS inflation", () => {
    const result = makeResult({
      incrementalROAS: { reportedROAS: 5, trueIncrementalROAS: 1.5, inflationRate: 0.7, totalSpend: 1000, reportedRevenue: 5000, incrementalRevenue: 1500 },
    });
    const alerts = runHealthChecks(result);
    const inflAlerts = alerts.filter((a) => a.metric === "inflationRate");
    expect(inflAlerts).toHaveLength(1);
    expect(inflAlerts[0].severity).toBe("critical");
  });

  it("flags warning ROAS inflation", () => {
    const result = makeResult({
      incrementalROAS: { reportedROAS: 4, trueIncrementalROAS: 2.5, inflationRate: 0.35, totalSpend: 1000, reportedRevenue: 4000, incrementalRevenue: 2500 },
    });
    const alerts = runHealthChecks(result);
    const inflAlerts = alerts.filter((a) => a.metric === "inflationRate");
    expect(inflAlerts).toHaveLength(1);
    expect(inflAlerts[0].severity).toBe("warning");
  });

  it("flags critical negative correlation", () => {
    const result = makeResult({ correlationMean: -0.3 });
    const alerts = runHealthChecks(result);
    const corrAlerts = alerts.filter((a) => a.metric === "correlationMean");
    expect(corrAlerts).toHaveLength(1);
    expect(corrAlerts[0].severity).toBe("critical");
  });

  it("flags warning weak correlation", () => {
    const result = makeResult({ correlationMean: 0.15 });
    const alerts = runHealthChecks(result);
    const corrAlerts = alerts.filter((a) => a.metric === "correlationMean");
    expect(corrAlerts).toHaveLength(1);
    expect(corrAlerts[0].severity).toBe("warning");
  });

  it("flags info when no GSC data provided", () => {
    const result = makeResult({ hasGSC: false });
    const alerts = runHealthChecks(result);
    const gscAlerts = alerts.filter((a) => a.metric === "gscData");
    expect(gscAlerts).toHaveLength(1);
    expect(gscAlerts[0].severity).toBe("info");
  });

  it("flags critical cannibalization score", () => {
    const result = makeResult({
      cannibalization: { cannibalizedDays: 10, totalDays: 20, cannibalizationScore: 0.5, cannibalizedRevenueFraction: 0.4 },
    });
    const alerts = runHealthChecks(result);
    const cannAlerts = alerts.filter((a) => a.metric === "cannibalizationScore");
    expect(cannAlerts).toHaveLength(1);
    expect(cannAlerts[0].severity).toBe("critical");
  });

  it("flags warning cannibalization score", () => {
    const result = makeResult({
      cannibalization: { cannibalizedDays: 6, totalDays: 20, cannibalizationScore: 0.3, cannibalizedRevenueFraction: 0.2 },
    });
    const alerts = runHealthChecks(result);
    const cannAlerts = alerts.filter((a) => a.metric === "cannibalizationScore");
    expect(cannAlerts).toHaveLength(1);
    expect(cannAlerts[0].severity).toBe("warning");
  });

  it("flags info for low organic baseline", () => {
    const result = makeResult({ organicBaselineConversions: 0.3 });
    const alerts = runHealthChecks(result);
    const baseAlerts = alerts.filter((a) => a.metric === "organicBaselineConversions");
    expect(baseAlerts).toHaveLength(1);
    expect(baseAlerts[0].severity).toBe("info");
  });

  it("respects custom thresholds", () => {
    const result = makeResult({
      deduplication: { platformReportedConversions: 100, actualConversions: 90, overlapCount: 90, duplicationRate: 0.1 },
    });
    const defaults = runHealthChecks(result);
    expect(defaults.filter((a) => a.metric === "duplicationRate")).toHaveLength(0);

    const custom: HealthCheckThresholds = { ...DEFAULT_THRESHOLDS, duplicationRateWarning: 0.08 };
    const customAlerts = runHealthChecks(result, custom);
    const dupAlerts = customAlerts.filter((a) => a.metric === "duplicationRate");
    expect(dupAlerts).toHaveLength(1);
  });

  it("sorts alerts by severity (critical first)", () => {
    const result = makeResult({
      deduplication: { platformReportedConversions: 100, actualConversions: 50, overlapCount: 50, duplicationRate: 0.5 },
      incrementalROAS: { reportedROAS: 4, trueIncrementalROAS: 2.5, inflationRate: 0.35, totalSpend: 1000, reportedRevenue: 4000, incrementalRevenue: 2500 },
      hasGSC: false,
    });
    const alerts = runHealthChecks(result);
    const severities = alerts.map((a) => a.severity);
    const order = { critical: 0, warning: 1, info: 2 } as const;
    for (let i = 0; i < severities.length - 1; i++) {
      expect(order[severities[i]]).toBeLessThanOrEqual(order[severities[i + 1]]);
    }
  });
});
