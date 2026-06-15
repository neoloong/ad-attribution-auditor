import type { AuditConfig, CannibalizationResult, DailyRow } from "./types";

function rollingMean(values: number[], window: number): number[] {
  const result: number[] = [];
  let sum = 0;
  for (let i = 0; i < values.length; i++) {
    sum += values[i];
    if (i >= window) sum -= values[i - window];
    result.push(sum / Math.min(i + 1, window));
  }
  return result;
}

export function computeCannibalization(
  daily: DailyRow[],
  config: AuditConfig,
): CannibalizationResult {
  if (!daily.length || daily.every((d) => d.brandClicks === 0)) {
    return {
      cannibalizedDays: 0,
      totalDays: 0,
      cannibalizationScore: 0,
      cannibalizedRevenueFraction: 0,
    };
  }

  const window = config.rollingAvgDays;
  const reportedConvs = daily.map((d) => d.reportedConversions);
  const brandClicks = daily.map((d) => d.brandClicks);

  const metaRollingAvg = rollingMean(reportedConvs, window);
  const brandRollingAvg = rollingMean(brandClicks, window);

  let cannibalizedDays = 0;
  let totalSpendOnDays = 0;

  for (let i = 0; i < daily.length; i++) {
    const metaAvg = metaRollingAvg[i] ?? 0;
    const brandAvg = brandRollingAvg[i] ?? 0;
    daily[i].metaRollingAvg = metaAvg;
    daily[i].brandRollingAvg = brandAvg;

    if (daily[i].spendOn) {
      totalSpendOnDays++;
      if (
        daily[i].reportedConversions > metaAvg &&
        daily[i].brandClicks > brandAvg
      ) {
        daily[i].cannibalized = true;
        cannibalizedDays++;
      } else {
        daily[i].cannibalized = false;
      }
    } else {
      daily[i].cannibalized = false;
    }
  }

  const spendOnRevenue = daily
    .filter((d) => d.spendOn)
    .reduce((s, d) => s + d.actualRevenue, 0);
  const cannibalizedRevenue = daily
    .filter((d) => d.cannibalized)
    .reduce((s, d) => s + d.actualRevenue, 0);

  const score = totalSpendOnDays > 0 ? cannibalizedDays / totalSpendOnDays : 0;
  const revFraction =
    spendOnRevenue > 0 ? cannibalizedRevenue / spendOnRevenue : 0;

  return {
    cannibalizedDays,
    totalDays: totalSpendOnDays,
    cannibalizationScore: Math.round(score * 10000) / 10000,
    cannibalizedRevenueFraction: Math.round(revFraction * 10000) / 10000,
  };
}
