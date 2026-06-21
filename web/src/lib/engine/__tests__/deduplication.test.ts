import { describe, it, expect } from "vitest";
import { computeDeduplication } from "../deduplication";
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

describe("computeDeduplication", () => {
  it("returns zero duplication when reported matches actual", () => {
    const daily = makeDaily([
      { reportedConversions: 5, actualConversions: 5 },
      { reportedConversions: 5, actualConversions: 5 },
    ]);
    const result = computeDeduplication(daily);
    expect(result.duplicationRate).toBe(0);
    expect(result.platformReportedConversions).toBe(10);
    expect(result.actualConversions).toBe(10);
  });

  it("detects duplication when platforms over-report", () => {
    const daily = makeDaily([
      { reportedConversions: 10, actualConversions: 5 },
      { reportedConversions: 10, actualConversions: 5 },
    ]);
    const result = computeDeduplication(daily);
    expect(result.duplicationRate).toBe(0.5);
    expect(result.overlapCount).toBe(10);
  });

  it("handles empty data", () => {
    const daily = makeDaily([{ reportedConversions: 0, actualConversions: 0 }]);
    const result = computeDeduplication(daily);
    expect(result.duplicationRate).toBe(0);
    expect(result.platformReportedConversions).toBe(0);
    expect(result.actualConversions).toBe(0);
  });

  it("handles actual conversions exceeding reported (under-reporting)", () => {
    const daily = makeDaily([
      { reportedConversions: 5, actualConversions: 10 },
    ]);
    const result = computeDeduplication(daily);
    expect(result.duplicationRate).toBe(0);
    expect(result.overlapCount).toBe(5);
  });

  it("handles all-zero case without NaN", () => {
    const daily: DailyRow[] = [];
    const result = computeDeduplication(daily);
    expect(result.duplicationRate).toBe(0);
    expect(result.platformReportedConversions).toBe(0);
    expect(result.actualConversions).toBe(0);
    expect(result.overlapCount).toBe(0);
  });
});
