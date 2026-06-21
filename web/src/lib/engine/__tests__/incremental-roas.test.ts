import { describe, it, expect } from "vitest";
import { computeIncrementalROAS } from "../incremental-roas";
import type { DailyRow } from "../types";

function makeDaily(overrides: Partial<DailyRow>[]): DailyRow[] {
  return overrides.map((row) => ({
    date: "2024-01-01",
    spend: 0,
    reportedConversions: 0,
    reportedRevenue: 0,
    actualConversions: 0,
    actualRevenue: 0,
    brandClicks: 0,
    brandImpressions: 0,
    spendOn: false,
    ...row,
  }));
}

describe("computeIncrementalROAS", () => {
  it("computes basic ROAS with an organic baseline", () => {
    const daily = makeDaily([
      { spend: 100, reportedRevenue: 500, actualRevenue: 400, actualConversions: 4, spendOn: true },
      { spend: 100, reportedRevenue: 500, actualRevenue: 400, actualConversions: 4, spendOn: true },
      { spend: 0, reportedRevenue: 0, actualRevenue: 100, actualConversions: 1, spendOn: false },
      { spend: 100, reportedRevenue: 500, actualRevenue: 400, actualConversions: 4, spendOn: true },
    ]);
    const result = computeIncrementalROAS(daily, 1.0);
    expect(result.reportedROAS).toBeGreaterThan(0);
    expect(result.trueIncrementalROAS).toBeGreaterThan(0);
    expect(result.trueIncrementalROAS).toBeLessThanOrEqual(result.reportedROAS);
    expect(result.totalSpend).toBe(300);
  });

  it("handles zero spend (all spend-off days)", () => {
    const daily = makeDaily([
      { spend: 0, reportedRevenue: 0, actualRevenue: 50, actualConversions: 1, spendOn: false },
      { spend: 0, reportedRevenue: 0, actualRevenue: 50, actualConversions: 1, spendOn: false },
    ]);
    const result = computeIncrementalROAS(daily, 1.0);
    expect(result.reportedROAS).toBe(0);
    expect(result.trueIncrementalROAS).toBe(0);
  });

  it("caps inflation rate when true ROAS exceeds reported", () => {
    const daily = makeDaily([
      { spend: 1, reportedRevenue: 1, actualRevenue: 100, actualConversions: 10, spendOn: true },
    ]);
    const result = computeIncrementalROAS(daily, 0.5);
    expect(result.trueIncrementalROAS).toBeGreaterThan(result.reportedROAS);
    expect(result.inflationRate).toBe(0);
  });

  it("caps inflation rate at 10 for tiny reported ROAS", () => {
    const daily = makeDaily([
      { spend: 100000, reportedRevenue: 100, actualRevenue: 10, actualConversions: 1, spendOn: true },
    ]);
    const result = computeIncrementalROAS(daily, 0);
    expect(result.inflationRate).toBeLessThanOrEqual(10);
  });

  it("handles zero actual conversions with non-zero revenue", () => {
    const daily = makeDaily([
      { spend: 100, reportedRevenue: 500, actualRevenue: 300, actualConversions: 0, spendOn: true },
    ]);
    const result = computeIncrementalROAS(daily, 1.0);
    expect(result.reportedROAS).toBe(5);
    expect(result.trueIncrementalROAS).toBeGreaterThanOrEqual(0);
    expect(result.inflationRate).toBeGreaterThanOrEqual(0);
  });

  it("sets incremental revenue to 0 when organic exceeds actual", () => {
    const daily = makeDaily([
      { spend: 100, reportedRevenue: 100, actualRevenue: 50, actualConversions: 1, spendOn: true },
    ]);
    const result = computeIncrementalROAS(daily, 10);
    expect(result.incrementalRevenue).toBe(0);
    expect(result.inflationRate).toBe(1);
  });

  it("uses correct avg revenue per conversion", () => {
    const daily = makeDaily([
      { spend: 100, reportedRevenue: 200, actualRevenue: 100, actualConversions: 2, spendOn: true },
      { spend: 0, reportedRevenue: 0, actualRevenue: 100, actualConversions: 2, spendOn: false },
    ]);
    const result = computeIncrementalROAS(daily, 1);
    // avgRevPerConv = 200/4 = 50, organicRevenue = 1 * 50 * 1 = 50
    // incrementalRevenue = max(0, 100 - 50) = 50
    // trueIncrementalROAS = 50/100 = 0.5
    expect(result.trueIncrementalROAS).toBe(0.5);
  });
});
