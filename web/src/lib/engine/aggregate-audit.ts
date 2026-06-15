import type { AuditConfig, AuditResult, DailyRow } from "./types";
import { DEFAULT_CONFIG } from "./types";
import { computeDeduplication } from "./deduplication";
import { computeCannibalization } from "./cannibalization";
import { computeIncrementalROAS } from "./incremental-roas";

export function runAggregateAudit(
  adDaily: { date: string; spend: number; reportedConversions: number; reportedRevenue: number }[],
  shopifyDaily: { date: string; actualConversions: number; actualRevenue: number }[],
  gscDaily?: { date: string; brandClicks: number; brandImpressions: number }[],
  config: AuditConfig = DEFAULT_CONFIG,
): AuditResult {
  const daily = buildDailyMerged(adDaily, shopifyDaily, gscDaily);

  for (const row of daily) {
    row.spendOn = row.spend >= config.spendOnThreshold;
  }

  const hasGSC = gscDaily !== undefined && gscDaily.length > 0;

  const organicBaseline = estimateOrganicBaseline(daily);
  const incrementalPerDay = computeIncrementalPerDay(daily, organicBaseline);
  const correlationMean = computeRollingCorrelation(daily, config.correlationWindowDays);

  const deduplication = computeDeduplication(daily);
  const cannibalization = hasGSC
    ? computeCannibalization(daily, config)
    : { cannibalizedDays: 0, totalDays: 0, cannibalizationScore: 0, cannibalizedRevenueFraction: 0 };
  const incrementalROAS = computeIncrementalROAS(daily, organicBaseline);

  return {
    config,
    deduplication,
    cannibalization,
    incrementalROAS,
    correlationMean: Math.round(correlationMean * 10000) / 10000,
    organicBaselineConversions: Math.round(organicBaseline * 100) / 100,
    incrementalConversionsPerDay: Math.round(incrementalPerDay * 100) / 100,
    dailyRows: daily,
    hasGSC,
  };
}

function buildDailyMerged(
  adDaily: { date: string; spend: number; reportedConversions: number; reportedRevenue: number }[],
  shopifyDaily: { date: string; actualConversions: number; actualRevenue: number }[],
  gscDaily?: { date: string; brandClicks: number; brandImpressions: number }[],
): DailyRow[] {
  const dateMap = new Map<string, DailyRow>();

  for (const a of adDaily) {
    const existing = dateMap.get(a.date);
    if (existing) {
      existing.spend += a.spend;
      existing.reportedConversions += a.reportedConversions;
      existing.reportedRevenue += a.reportedRevenue;
    } else {
      dateMap.set(a.date, {
        date: a.date,
        spend: a.spend,
        reportedConversions: a.reportedConversions,
        reportedRevenue: a.reportedRevenue,
        actualConversions: 0,
        actualRevenue: 0,
        brandClicks: 0,
        brandImpressions: 0,
        spendOn: false,
      });
    }
  }

  for (const s of shopifyDaily) {
    const existing = dateMap.get(s.date);
    if (existing) {
      existing.actualConversions += s.actualConversions;
      existing.actualRevenue += s.actualRevenue;
    } else {
      dateMap.set(s.date, {
        date: s.date,
        spend: 0,
        reportedConversions: 0,
        reportedRevenue: 0,
        actualConversions: s.actualConversions,
        actualRevenue: s.actualRevenue,
        brandClicks: 0,
        brandImpressions: 0,
        spendOn: false,
      });
    }
  }

  if (gscDaily) {
    for (const g of gscDaily) {
      const existing = dateMap.get(g.date);
      if (existing) {
        existing.brandClicks += g.brandClicks;
        existing.brandImpressions += g.brandImpressions;
      } else {
        dateMap.set(g.date, {
          date: g.date,
          spend: 0,
          reportedConversions: 0,
          reportedRevenue: 0,
          actualConversions: 0,
          actualRevenue: 0,
          brandClicks: g.brandClicks,
          brandImpressions: g.brandImpressions,
          spendOn: false,
        });
      }
    }
  }

  const rows = Array.from(dateMap.values());
  rows.sort((a, b) => a.date.localeCompare(b.date));
  return rows;
}

function estimateOrganicBaseline(daily: DailyRow[]): number {
  // Method 1: OLS regression (need >= 60 days)
  if (daily.length >= 60) {
    const baseline = regressionBaseline(daily);
    if (baseline !== null) return baseline;
  }

  // Method 2: Time-series interruption (>= 7 consecutive spend-off days)
  const interruption = interruptionBaseline(daily);
  if (interruption !== null) return Math.max(0, interruption);

  // Method 3: Average conversions on spend-off days
  const offDays = daily.filter((d) => !d.spendOn);
  if (offDays.length > 0) {
    return offDays.reduce((s, d) => s + d.actualConversions, 0) / offDays.length;
  }

  return 0;
}

function regressionBaseline(daily: DailyRow[]): number | null {
  const n = daily.length;
  const spend = daily.map((d) => d.spend);
  const conv = daily.map((d) => d.actualConversions);

  const spendMean = spend.reduce((s, v) => s + v, 0) / n;
  const spendStd = Math.sqrt(spend.reduce((s, v) => s + (v - spendMean) ** 2, 0) / n);
  if (spendStd < 1) return null;

  const zeroSpendDays = spend.filter((v) => v === 0).length;
  if (zeroSpendDays < 3) return null;

  // OLS: intercept = mean(y) - slope * mean(x)
  const convMean = conv.reduce((s, v) => s + v, 0) / n;
  let cov = 0;
  let varX = 0;
  for (let i = 0; i < n; i++) {
    cov += (spend[i] - spendMean) * (conv[i] - convMean);
    varX += (spend[i] - spendMean) ** 2;
  }
  if (varX === 0) return null;
  const slope = cov / varX;
  const intercept = convMean - slope * spendMean;

  if (intercept < 0) return null;

  // R² check
  let ssRes = 0;
  let ssTot = 0;
  for (let i = 0; i < n; i++) {
    const yHat = intercept + slope * spend[i];
    ssRes += (conv[i] - yHat) ** 2;
    ssTot += (conv[i] - convMean) ** 2;
  }
  const r2 = ssTot > 0 ? 1 - ssRes / ssTot : 0;
  if (r2 < 0.01) return null;

  return intercept;
}

function interruptionBaseline(daily: DailyRow[]): number | null {
  const MIN_INTERRUPTION = 7;
  let bestStart = -1;
  let bestLen = 0;
  let currentStart = -1;
  let currentLen = 0;

  for (let i = 0; i < daily.length; i++) {
    if (!daily[i].spendOn) {
      if (currentLen === 0) currentStart = i;
      currentLen++;
      if (currentLen > bestLen) {
        bestLen = currentLen;
        bestStart = currentStart;
      }
    } else {
      currentLen = 0;
    }
  }

  if (bestLen >= MIN_INTERRUPTION && bestStart >= 0) {
    const streak = daily.slice(bestStart, bestStart + bestLen);
    return streak.reduce((s, d) => s + d.actualConversions, 0) / streak.length;
  }

  return null;
}

function computeIncrementalPerDay(daily: DailyRow[], organicBaseline: number): number {
  const onDays = daily.filter((d) => d.spendOn);
  if (onDays.length === 0) return 0;
  const onAvg = onDays.reduce((s, d) => s + d.actualConversions, 0) / onDays.length;
  return Math.max(0, onAvg - organicBaseline);
}

function computeRollingCorrelation(daily: DailyRow[], window: number): number {
  const n = daily.length;
  if (n < 2) return 0;

  const spend = daily.map((d) => d.spend);
  const conv = daily.map((d) => d.actualConversions);

  if (n < window) {
    return pearsonCorrelation(spend, conv);
  }

  const rollingRs: number[] = [];
  for (let i = window - 1; i < n; i++) {
    const sliceSpend = spend.slice(i - window + 1, i + 1);
    const sliceConv = conv.slice(i - window + 1, i + 1);
    const r = pearsonCorrelation(sliceSpend, sliceConv);
    if (isFinite(r)) rollingRs.push(r);
  }

  if (rollingRs.length === 0) return 0;
  return rollingRs.reduce((s, r) => s + r, 0) / rollingRs.length;
}

function pearsonCorrelation(x: number[], y: number[]): number {
  const n = x.length;
  const xMean = x.reduce((s, v) => s + v, 0) / n;
  const yMean = y.reduce((s, v) => s + v, 0) / n;

  let cov = 0;
  let varX = 0;
  let varY = 0;

  for (let i = 0; i < n; i++) {
    const dx = x[i] - xMean;
    const dy = y[i] - yMean;
    cov += dx * dy;
    varX += dx * dx;
    varY += dy * dy;
  }

  if (varX === 0 || varY === 0) return 0;
  return cov / Math.sqrt(varX * varY);
}
