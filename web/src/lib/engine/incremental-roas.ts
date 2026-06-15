import type { DailyRow, IncrementalROASResult } from "./types";

export function computeIncrementalROAS(
  daily: DailyRow[],
  organicBaseline: number,
): IncrementalROASResult {
  const totalSpend = daily.reduce((s, d) => s + d.spend, 0);
  const reportedRevenue = daily.reduce((s, d) => s + d.reportedRevenue, 0);
  const spendOnRows = daily.filter((d) => d.spendOn);
  const spendOnDays = spendOnRows.length;
  const actualRevenueOn = spendOnRows.reduce((s, d) => s + d.actualRevenue, 0);
  const actualConvSum = daily.reduce((s, d) => s + d.actualConversions, 0);
  const actualRevenueTotal = daily.reduce((s, d) => s + d.actualRevenue, 0);

  const avgRevPerConv =
    actualConvSum > 0 ? actualRevenueTotal / actualConvSum : 0;

  const organicRevenue = organicBaseline * avgRevPerConv * spendOnDays;
  const incrementalRevenue = Math.max(0, actualRevenueOn - organicRevenue);

  const reportedROAS = totalSpend > 0 ? reportedRevenue / totalSpend : 0;
  const trueROAS = totalSpend > 0 ? incrementalRevenue / totalSpend : 0;

  let inflation = 0;
  if (reportedROAS > 0.01) {
    inflation = (reportedROAS - trueROAS) / reportedROAS;
  }
  inflation = Math.max(0, Math.min(inflation, 10));

  return {
    reportedROAS: Math.round(reportedROAS * 10000) / 10000,
    trueIncrementalROAS: Math.round(trueROAS * 10000) / 10000,
    inflationRate: Math.round(inflation * 10000) / 10000,
    totalSpend: Math.round(totalSpend * 100) / 100,
    reportedRevenue: Math.round(reportedRevenue * 100) / 100,
    incrementalRevenue: Math.round(incrementalRevenue * 100) / 100,
  };
}
