"use client";

export const dynamic = "force-dynamic";

import { useMemo } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Button, buttonVariants } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { useAuditStore } from "@/lib/store/use-audit-store";
import { runHealthChecks } from "@/lib/engine";
import { ArrowLeft, Download, Sparkles } from "lucide-react";

export default function ReportPage() {
  const router = useRouter();
  const store = useAuditStore();
  const { auditResult } = store;

  const alerts = useMemo(
    () => (auditResult ? runHealthChecks(auditResult) : []),
    [auditResult],
  );

  if (!auditResult) {
    router.replace("/upload");
    return null;
  }

  const { deduplication, cannibalization, incrementalROAS } = auditResult;

  const reportText = `
========================================
AD ATTRIBUTION AUDIT REPORT
========================================
Date Generated: ${new Date().toISOString().slice(0, 10)}
Period: ${auditResult.dailyRows[0]?.date} → ${auditResult.dailyRows[auditResult.dailyRows.length - 1]?.date}
Days Analyzed: ${auditResult.dailyRows.length}

--- KEY METRICS ---
Reported ROAS: ${incrementalROAS.reportedROAS.toFixed(2)}x
True Incremental ROAS: ${incrementalROAS.trueIncrementalROAS.toFixed(2)}x
ROAS Inflation Rate: ${(incrementalROAS.inflationRate * 100).toFixed(0)}%
Total Ad Spend: $${incrementalROAS.totalSpend.toLocaleString()}
Reported Revenue: $${incrementalROAS.reportedRevenue.toLocaleString()}
Incremental Revenue: $${incrementalROAS.incrementalRevenue.toLocaleString()}

--- DE-DUPLICATION ---
Platform Reported Conversions: ${deduplication.platformReportedConversions}
Actual Shopify Conversions: ${deduplication.actualConversions}
Duplicate Overlap: ${deduplication.overlapCount}
Duplication Rate: ${(deduplication.duplicationRate * 100).toFixed(0)}%

--- CANNIBALIZATION ---
Cannibalized Days: ${cannibalization.cannibalizedDays}/${cannibalization.totalDays} spend-on days
Cannibalization Score: ${(cannibalization.cannibalizationScore * 100).toFixed(0)}%
Cannibalized Revenue Fraction: ${(cannibalization.cannibalizedRevenueFraction * 100).toFixed(0)}%

--- CORRELATION ---
Spend-Conversion Correlation: ${auditResult.correlationMean.toFixed(3)}
Organic Baseline: ${auditResult.organicBaselineConversions.toFixed(1)} conversions/day
Incremental Conversions: ${auditResult.incrementalConversionsPerDay.toFixed(1)}/day

--- HEALTH ALERTS ---
${alerts.length > 0
    ? alerts.map((a) => `[${a.severity.toUpperCase()}] ${a.title}\n${a.message}\n`).join("\n")
    : "No alerts. Metrics are within healthy ranges."
}
========================================
`.trim();

  const downloadReport = () => {
    const blob = new Blob([reportText], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `ad-attribution-audit-${new Date().toISOString().slice(0, 10)}.txt`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="flex flex-col min-h-screen">
      <header className="sticky top-0 z-50 border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
        <div className="container mx-auto flex h-14 items-center justify-between px-4">
          <div className="flex items-center gap-3">
            <Link
              href="/dashboard"
              className={cn(buttonVariants({ variant: "ghost", size: "sm" }))}
            >
              <ArrowLeft className="h-4 w-4 mr-1" /> Dashboard
            </Link>
            <span className="font-semibold">Audit Report</span>
          </div>
          <Button variant="outline" size="sm" onClick={downloadReport}>
            <Download className="mr-2 h-4 w-4" /> Download Report
          </Button>
        </div>
      </header>

      <main className="flex-1 container mx-auto px-4 py-8 max-w-3xl">
        <Card className="mb-8">
          <CardHeader>
            <div className="flex items-center gap-2 mb-2">
              <Sparkles className="h-5 w-5 text-purple-500" />
              <Badge variant="secondary">Premium Feature — Coming Soon</Badge>
            </div>
            <CardTitle>AI-Powered Report</CardTitle>
            <CardDescription>
              In the full version, our LLM-powered engine will analyze your audit results
              and generate a plain-English executive summary with actionable recommendations.
            </CardDescription>
          </CardHeader>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Audit Summary</CardTitle>
          </CardHeader>
          <CardContent>
            <pre className="whitespace-pre-wrap text-sm font-mono bg-muted p-4 rounded-lg overflow-auto max-h-[600px]">
              {reportText}
            </pre>
          </CardContent>
        </Card>
      </main>
    </div>
  );
}
