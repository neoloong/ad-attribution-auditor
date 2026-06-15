import Papa from "papaparse";
import type { AdDaily, GSCDaily, ShopifyDaily } from "./types";

function parseDate(raw: string): string {
  // Handle various date formats: "2024-01-01", "Jan 1, 2024", "2024-01-01 00:46:08"
  const trimmed = raw.trim();
  // Try ISO date extraction
  const isoMatch = trimmed.match(/^(\d{4}-\d{2}-\d{2})/);
  if (isoMatch) return isoMatch[1];

  // Try parsing as full date
  const d = new Date(trimmed);
  if (!isNaN(d.getTime())) {
    return d.toISOString().slice(0, 10);
  }

  return trimmed;
}

function parseNumber(val: string): number {
  const n = Number(val.replace(/[$,]/g, "").trim());
  return isNaN(n) ? 0 : n;
}

export function normalizeMetaAds(csvContent: string): AdDaily[] {
  const result = Papa.parse<Record<string, string>>(csvContent, {
    header: true,
    skipEmptyLines: true,
  });

  const dateMap = new Map<string, AdDaily>();

  for (const row of result.data) {
    const date = parseDate(row["Day"] ?? "");
    const spend = parseNumber(row["Amount spent (USD)"] ?? "0");
    const conversions = parseNumber(row["Purchases"] ?? "0");
    const revenue = parseNumber(row["Purchase conversion value"] ?? "0");

    if (!date) continue;

    const existing = dateMap.get(date);
    if (existing) {
      existing.spend += spend;
      existing.reportedConversions += conversions;
      existing.reportedRevenue += revenue;
    } else {
      dateMap.set(date, { date, spend, reportedConversions: conversions, reportedRevenue: revenue });
    }
  }

  return Array.from(dateMap.values()).sort((a, b) => a.date.localeCompare(b.date));
}

export function normalizeGoogleAds(csvContent: string): AdDaily[] {
  const result = Papa.parse<Record<string, string>>(csvContent, {
    header: true,
    skipEmptyLines: true,
  });

  const dateMap = new Map<string, AdDaily>();

  for (const row of result.data) {
    const date = parseDate(row["Day"] ?? "");
    const spend = parseNumber(row["Cost"] ?? "0");
    const conversions = parseNumber(row["Conversions"] ?? "0");
    const revenue = parseNumber(row["Conv. value"] ?? "0");

    if (!date) continue;

    const existing = dateMap.get(date);
    if (existing) {
      existing.spend += spend;
      existing.reportedConversions += conversions;
      existing.reportedRevenue += revenue;
    } else {
      dateMap.set(date, { date, spend, reportedConversions: conversions, reportedRevenue: revenue });
    }
  }

  return Array.from(dateMap.values()).sort((a, b) => a.date.localeCompare(b.date));
}

export function normalizeShopifyOrders(csvContent: string): ShopifyDaily[] {
  const result = Papa.parse<Record<string, string>>(csvContent, {
    header: true,
    skipEmptyLines: true,
  });

  const dateMap = new Map<string, ShopifyDaily>();

  for (const row of result.data) {
    const date = parseDate(row["Created at"] ?? "");
    const revenue = parseNumber(row["Total"] ?? "0");

    if (!date) continue;

    const existing = dateMap.get(date);
    if (existing) {
      existing.actualConversions += 1;
      existing.actualRevenue += revenue;
    } else {
      dateMap.set(date, { date, actualConversions: 1, actualRevenue: revenue });
    }
  }

  return Array.from(dateMap.values()).sort((a, b) => a.date.localeCompare(b.date));
}

export function normalizeGSC(csvContent: string): GSCDaily[] {
  const result = Papa.parse<Record<string, string>>(csvContent, {
    header: true,
    skipEmptyLines: true,
  });

  const dateMap = new Map<string, GSCDaily>();

  for (const row of result.data) {
    const date = parseDate(row["Date"] ?? "");
    const clicks = parseNumber(row["Clicks"] ?? "0");
    const impressions = parseNumber(row["Impressions"] ?? "0");

    if (!date) continue;

    const existing = dateMap.get(date);
    if (existing) {
      existing.brandClicks += clicks;
      existing.brandImpressions += impressions;
    } else {
      dateMap.set(date, { date, brandClicks: clicks, brandImpressions: impressions });
    }
  }

  return Array.from(dateMap.values()).sort((a, b) => a.date.localeCompare(b.date));
}

export function mergeAdDaily(metaAds: AdDaily[], googleAds: AdDaily[]): AdDaily[] {
  const dateMap = new Map<string, AdDaily>();

  for (const row of [...metaAds, ...googleAds]) {
    const existing = dateMap.get(row.date);
    if (existing) {
      existing.spend += row.spend;
      existing.reportedConversions += row.reportedConversions;
      existing.reportedRevenue += row.reportedRevenue;
    } else {
      dateMap.set(row.date, { ...row });
    }
  }

  return Array.from(dateMap.values()).sort((a, b) => a.date.localeCompare(b.date));
}
