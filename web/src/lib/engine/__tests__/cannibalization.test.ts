import { describe, it, expect } from "vitest";
import { computeCannibalization } from "../cannibalization";
import type { AuditConfig, DailyRow } from "../types";
import { DEFAULT_CONFIG } from "../types";

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

describe("computeCannibalization", () => {
  const config: AuditConfig = { ...DEFAULT_CONFIG, rollingAvgDays: 3 };

  it("detects no cannibalization when all values at average", () => {
    const daily = makeDaily([
      { reportedConversions: 5, brandClicks: 1, spendOn: true, spend: 100, actualRevenue: 500 },
      { reportedConversions: 5, brandClicks: 1, spendOn: true, spend: 100, actualRevenue: 500 },
      { reportedConversions: 5, brandClicks: 1, spendOn: true, spend: 100, actualRevenue: 500 },
    ]);
    const result = computeCannibalization(daily, config);
    expect(result.cannibalizedDays).toBe(0);
    expect(result.cannibalizationScore).toBe(0);
  });

  it("detects cannibalization when conversions and brand clicks spike", () => {
    const daily = makeDaily([
      { reportedConversions: 2, brandClicks: 3, spendOn: true, spend: 100, actualRevenue: 200 },
      { reportedConversions: 2, brandClicks: 3, spendOn: true, spend: 100, actualRevenue: 200 },
      { reportedConversions: 2, brandClicks: 3, spendOn: true, spend: 100, actualRevenue: 200 },
      { reportedConversions: 10, brandClicks: 15, spendOn: true, spend: 100, actualRevenue: 1000 },
      { reportedConversions: 10, brandClicks: 15, spendOn: true, spend: 100, actualRevenue: 1000 },
    ]);
    const result = computeCannibalization(daily, config);
    expect(result.cannibalizedDays).toBeGreaterThan(0);
    expect(result.cannibalizationScore).toBeGreaterThan(0);
  });

  it("returns zero when all brand clicks are zero", () => {
    const daily = makeDaily([
      { reportedConversions: 5, brandClicks: 0, spendOn: true, spend: 100, actualRevenue: 500 },
    ]);
    const result = computeCannibalization(daily, config);
    expect(result.cannibalizationScore).toBe(0);
  });

  it("returns zero for empty input", () => {
    const daily: DailyRow[] = [];
    const result = computeCannibalization(daily, config);
    expect(result.cannibalizationScore).toBe(0);
    expect(result.totalDays).toBe(0);
  });

  it("does not flag non-spend-on days as cannibalized", () => {
    const daily = makeDaily([
      { reportedConversions: 10, brandClicks: 15, spendOn: false, spend: 0, actualRevenue: 1000 },
      { reportedConversions: 10, brandClicks: 15, spendOn: false, spend: 0, actualRevenue: 1000 },
    ]);
    // Both have zero spend → spendOn is false → neither flagged
    const result = computeCannibalization(daily, config);
    expect(result.totalDays).toBe(0);
    expect(result.cannibalizedDays).toBe(0);
  });

  it("sets cannibalizedRevenueFraction correctly", () => {
    const daily = makeDaily([
      { reportedConversions: 2, brandClicks: 3, spendOn: true, spend: 100, actualRevenue: 200 },
      { reportedConversions: 2, brandClicks: 3, spendOn: true, spend: 100, actualRevenue: 200 },
      { reportedConversions: 2, brandClicks: 3, spendOn: true, spend: 100, actualRevenue: 200 },
      { reportedConversions: 10, brandClicks: 15, spendOn: true, spend: 100, actualRevenue: 1000 },
    ]);
    const result = computeCannibalization(daily, config);
    expect(result.cannibalizedRevenueFraction).toBeGreaterThan(0);
    expect(result.cannibalizedRevenueFraction).toBeLessThanOrEqual(1);
  });
});
