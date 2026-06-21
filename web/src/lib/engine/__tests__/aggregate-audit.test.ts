import { describe, it, expect } from "vitest";
import { runAggregateAudit } from "../aggregate-audit";
import type { AuditConfig } from "../types";
import { DEFAULT_CONFIG } from "../types";

describe("runAggregateAudit", () => {
  const config: AuditConfig = { ...DEFAULT_CONFIG };

  it("runs a full audit with ad and shopify data", () => {
    const adDaily = [
      { date: "2024-01-01", spend: 100, reportedConversions: 5, reportedRevenue: 500 },
      { date: "2024-01-02", spend: 100, reportedConversions: 5, reportedRevenue: 500 },
      { date: "2024-01-03", spend: 0, reportedConversions: 0, reportedRevenue: 0 },
      { date: "2024-01-04", spend: 100, reportedConversions: 8, reportedRevenue: 800 },
    ];
    const shopifyDaily = [
      { date: "2024-01-01", actualConversions: 4, actualRevenue: 400 },
      { date: "2024-01-02", actualConversions: 4, actualRevenue: 400 },
      { date: "2024-01-03", actualConversions: 1, actualRevenue: 100 },
      { date: "2024-01-04", actualConversions: 6, actualRevenue: 600 },
    ];

    const result = runAggregateAudit(adDaily, shopifyDaily, undefined, config);

    expect(result.dailyRows).toHaveLength(4);
    expect(result.incrementalROAS.totalSpend).toBe(300);
    expect(result.incrementalROAS.reportedRevenue).toBeGreaterThan(0);
    expect(result.organicBaselineConversions).toBeGreaterThanOrEqual(0);
    expect(result.incrementalConversionsPerDay).toBeGreaterThanOrEqual(0);
    expect(result.hasGSC).toBe(false);
  });

  it("runs with both Meta and Google Ads data combined", () => {
    const metaAds = [
      { date: "2024-01-01", spend: 100, reportedConversions: 3, reportedRevenue: 300 },
      { date: "2024-01-02", spend: 150, reportedConversions: 4, reportedRevenue: 400 },
    ];
    const googleAds = [
      { date: "2024-01-01", spend: 50, reportedConversions: 2, reportedRevenue: 200 },
      { date: "2024-01-02", spend: 80, reportedConversions: 2, reportedRevenue: 180 },
    ];
    const shopifyDaily = [
      { date: "2024-01-01", actualConversions: 4, actualRevenue: 400 },
      { date: "2024-01-02", actualConversions: 5, actualRevenue: 500 },
    ];

    const allAds = [...metaAds, ...googleAds];
    const result = runAggregateAudit(allAds, shopifyDaily, undefined, config);

    expect(result.dailyRows).toHaveLength(2);
    expect(result.incrementalROAS.totalSpend).toBe(380);
  });

  it("works without GSC data (graceful degradation)", () => {
    const adDaily = [
      { date: "2024-01-01", spend: 100, reportedConversions: 5, reportedRevenue: 500 },
    ];
    const shopifyDaily = [
      { date: "2024-01-01", actualConversions: 4, actualRevenue: 400 },
    ];

    const result = runAggregateAudit(adDaily, shopifyDaily, undefined, config);

    expect(result.hasGSC).toBe(false);
    expect(result.cannibalization.cannibalizationScore).toBe(0);
    expect(result.cannibalization.totalDays).toBe(0);
  });

  it("runs full audit with GSC data", () => {
    const adDaily = [
      { date: "2024-01-01", spend: 100, reportedConversions: 5, reportedRevenue: 500 },
      { date: "2024-01-02", spend: 100, reportedConversions: 5, reportedRevenue: 500 },
      { date: "2024-01-03", spend: 0, reportedConversions: 0, reportedRevenue: 0 },
      { date: "2024-01-04", spend: 100, reportedConversions: 8, reportedRevenue: 800 },
      { date: "2024-01-05", spend: 100, reportedConversions: 6, reportedRevenue: 600 },
    ];
    const shopifyDaily = [
      { date: "2024-01-01", actualConversions: 4, actualRevenue: 400 },
      { date: "2024-01-02", actualConversions: 4, actualRevenue: 400 },
      { date: "2024-01-03", actualConversions: 1, actualRevenue: 100 },
      { date: "2024-01-04", actualConversions: 6, actualRevenue: 600 },
      { date: "2024-01-05", actualConversions: 5, actualRevenue: 500 },
    ];
    const gscDaily = [
      { date: "2024-01-01", brandClicks: 10, brandImpressions: 100 },
      { date: "2024-01-02", brandClicks: 12, brandImpressions: 110 },
      { date: "2024-01-03", brandClicks: 8, brandImpressions: 90 },
      { date: "2024-01-04", brandClicks: 15, brandImpressions: 130 },
      { date: "2024-01-05", brandClicks: 11, brandImpressions: 105 },
    ];

    const result = runAggregateAudit(adDaily, shopifyDaily, gscDaily, config);

    expect(result.hasGSC).toBe(true);
    expect(result.dailyRows.every((r) => r.brandClicks >= 0)).toBe(true);
  });

  it("uses interruption baseline when spend-off period is 7+ days", () => {
    const adDaily: { date: string; spend: number; reportedConversions: number; reportedRevenue: number }[] = [];
    const shopifyDaily: { date: string; actualConversions: number; actualRevenue: number }[] = [];

    for (let i = 0; i < 10; i++) {
      const d = `2024-01-${String(i + 1).padStart(2, "0")}`;
      adDaily.push({ date: d, spend: i >= 3 ? 100 : 0, reportedConversions: i >= 3 ? 5 : 0, reportedRevenue: i >= 3 ? 500 : 0 });
      shopifyDaily.push({ date: d, actualConversions: i >= 3 ? 5 : 2, actualRevenue: i >= 3 ? 500 : 200 });
    }

    const result = runAggregateAudit(adDaily, shopifyDaily, undefined, config);
    expect(result.organicBaselineConversions).toBe(2); // 3 off days with 2 conversions each
  });

  it("handles single-day data", () => {
    const adDaily = [
      { date: "2024-01-01", spend: 100, reportedConversions: 5, reportedRevenue: 500 },
    ];
    const shopifyDaily = [
      { date: "2024-01-01", actualConversions: 4, actualRevenue: 400 },
    ];

    const result = runAggregateAudit(adDaily, shopifyDaily, undefined, config);
    expect(result.dailyRows).toHaveLength(1);
    expect(result.correlationMean).toBe(0);
  });

  it("handles date gaps (shopify days without ad spend)", () => {
    const adDaily = [
      { date: "2024-01-01", spend: 100, reportedConversions: 5, reportedRevenue: 500 },
      { date: "2024-01-03", spend: 100, reportedConversions: 5, reportedRevenue: 500 },
    ];
    const shopifyDaily = [
      { date: "2024-01-01", actualConversions: 4, actualRevenue: 400 },
      { date: "2024-01-02", actualConversions: 3, actualRevenue: 300 },
      { date: "2024-01-03", actualConversions: 4, actualRevenue: 400 },
    ];

    const result = runAggregateAudit(adDaily, shopifyDaily, undefined, config);
    expect(result.dailyRows).toHaveLength(3);
    // Day 2024-01-02 has no ad data (spend=0) but has shopify data
  });

  it("dailyRows are sorted by date", () => {
    const adDaily = [
      { date: "2024-03-01", spend: 100, reportedConversions: 5, reportedRevenue: 500 },
      { date: "2024-01-01", spend: 100, reportedConversions: 5, reportedRevenue: 500 },
      { date: "2024-02-01", spend: 100, reportedConversions: 5, reportedRevenue: 500 },
    ];
    const shopifyDaily = [
      { date: "2024-03-01", actualConversions: 4, actualRevenue: 400 },
      { date: "2024-01-01", actualConversions: 4, actualRevenue: 400 },
      { date: "2024-02-01", actualConversions: 4, actualRevenue: 400 },
    ];

    const result = runAggregateAudit(adDaily, shopifyDaily, undefined, config);
    expect(result.dailyRows[0].date).toBe("2024-01-01");
    expect(result.dailyRows[1].date).toBe("2024-02-01");
    expect(result.dailyRows[2].date).toBe("2024-03-01");
  });

  it("uses OLS regression baseline with 60+ days of varied spend", () => {
    const adDaily: { date: string; spend: number; reportedConversions: number; reportedRevenue: number }[] = [];
    const shopifyDaily: { date: string; actualConversions: number; actualRevenue: number }[] = [];

    for (let i = 0; i < 65; i++) {
      const d = `2024-01-${String(i + 1).padStart(2, "0")}`;
      const spend = i % 7 === 0 ? 0 : 50 + Math.random() * 200;
      const organic = 2;
      const driven = spend * 0.1;
      const conv = Math.round(organic + driven + (Math.random() - 0.5) * 2);
      adDaily.push({ date: d, spend: Math.round(spend), reportedConversions: Math.round(conv * 1.3), reportedRevenue: Math.round(conv * 50 * 1.3) });
      shopifyDaily.push({ date: d, actualConversions: Math.max(0, conv), actualRevenue: Math.max(0, conv * 50) });
    }

    const result = runAggregateAudit(adDaily, shopifyDaily, undefined, config);
    expect(result.organicBaselineConversions).toBeGreaterThan(0);
    expect(result.organicBaselineConversions).toBeLessThan(5);
  });
});
