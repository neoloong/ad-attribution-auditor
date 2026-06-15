import type { AuditResult, DailyRow } from "@/lib/engine";
import { runAggregateAudit } from "@/lib/engine/aggregate-audit";

function randomInt(min: number, max: number): number {
  return Math.floor(Math.random() * (max - min + 1)) + min;
}

function randomFloat(min: number, max: number, decimals = 2): number {
  return Number((Math.random() * (max - min) + min).toFixed(decimals));
}

function generateDateArray(days: number): string[] {
  const dates: string[] = [];
  const start = new Date("2024-01-01");
  for (let i = 0; i < days; i++) {
    const d = new Date(start);
    d.setDate(d.getDate() + i);
    dates.push(d.toISOString().slice(0, 10));
  }
  return dates;
}

export function generateDemoResult(): AuditResult {
  const dates = generateDateArray(180);
  const dailyRows: DailyRow[] = [];

  for (let i = 0; i < dates.length; i++) {
    // Simulate spend pattern: ~70% of days have spend
    const hasSpend = Math.random() > 0.3;
    const spend = hasSpend ? randomFloat(50, 350) : 0;
    const spendOn = spend >= 5;

    // Base conversions: organic ~3/day + spend-driven ~0.15 * spend
    const organicBase = randomFloat(1, 5);
    const spendDriven = spend * 0.12;
    const actualConversions = Math.max(0, Math.round(organicBase + spendDriven + randomFloat(-2, 2)));

    // Ad platforms report more than actual (inflation)
    const reportedConversions = hasSpend
      ? Math.round(actualConversions * randomFloat(1.1, 2.0))
      : 0;

    const avgOrderValue = randomFloat(45, 85);
    const actualRevenue = actualConversions * avgOrderValue;
    const reportedRevenue = reportedConversions * avgOrderValue;

    const brandClicks = randomInt(5, 30);
    const brandImpressions = brandClicks * randomInt(5, 15);

    dailyRows.push({
      date: dates[i],
      spend,
      reportedConversions,
      reportedRevenue,
      actualConversions,
      actualRevenue,
      brandClicks,
      brandImpressions,
      spendOn,
    });
  }

  // Run the actual audit on the demo data
  const result = runAggregateAudit(
    dailyRows.map((d) => ({
      date: d.date,
      spend: d.spend,
      reportedConversions: d.reportedConversions,
      reportedRevenue: d.reportedRevenue,
    })),
    dailyRows.map((d) => ({
      date: d.date,
      actualConversions: d.actualConversions,
      actualRevenue: d.actualRevenue,
    })),
    dailyRows.map((d) => ({
      date: d.date,
      brandClicks: d.brandClicks,
      brandImpressions: d.brandImpressions,
    })),
  );

  return result;
}
