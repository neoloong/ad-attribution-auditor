import type { DailyRow, DeduplicationResult } from "./types";

export function computeDeduplication(daily: DailyRow[]): DeduplicationResult {
  const platformTotal = daily.reduce((s, d) => s + d.reportedConversions, 0);
  const actualTotal = daily.reduce((s, d) => s + d.actualConversions, 0);

  if (platformTotal === 0 && actualTotal === 0) {
    return {
      platformReportedConversions: 0,
      actualConversions: 0,
      overlapCount: 0,
      duplicationRate: 0,
    };
  }

  const overlap = daily.reduce(
    (s, d) => s + Math.min(d.reportedConversions, d.actualConversions),
    0,
  );
  const excess = Math.max(0, platformTotal - actualTotal);
  const dupRate = platformTotal > 0 ? excess / platformTotal : 0;

  return {
    platformReportedConversions: platformTotal,
    actualConversions: actualTotal,
    overlapCount: Math.floor(overlap),
    duplicationRate: Math.round(dupRate * 10000) / 10000,
  };
}
