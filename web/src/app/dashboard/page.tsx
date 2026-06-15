"use client";

export const dynamic = "force-dynamic";

import { useEffect, useMemo } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { buttonVariants } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useAuditStore } from "@/lib/store/use-audit-store";
import { runHealthChecks } from "@/lib/engine";
import type { HealthCheckAlert } from "@/lib/engine";
import { generateDemoResult } from "./demo-data";
import { setStore } from "@/lib/store/audit-store";
import {
  ArrowLeft,
  TrendingUp,
  TrendingDown,
  AlertTriangle,
  Info,
  DollarSign,
  BarChart3,
  Target,
} from "lucide-react";
import nextDynamic from "next/dynamic";

const ROASChart = nextDynamic(() => import("./roas-chart"), { ssr: false });
const DuplicationChart = nextDynamic(() => import("./duplication-chart"), { ssr: false });
const CannibalizationChart = nextDynamic(() => import("./cannibalization-chart"), { ssr: false });
const TrendChart = nextDynamic(() => import("./trend-chart"), { ssr: false });

export default function DashboardPage() {
  const router = useRouter();
  const store = useAuditStore();
  const { auditResult } = store;

  // Support demo mode via query param
  useEffect(() => {
    if (typeof window === "undefined") return;
    const params = new URLSearchParams(window.location.search);
    if (params.get("demo") === "true" && !auditResult) {
      const demo = generateDemoResult();
      setStore({ auditResult: demo });
    }
  }, [auditResult]);

  useEffect(() => {
    if (typeof window === "undefined" || auditResult) return;
    const params = new URLSearchParams(window.location.search);
    if (params.get("demo") !== "true") {
      router.replace("/upload");
    }
  }, [auditResult, router]);

  const alerts: HealthCheckAlert[] = useMemo(
    () => (auditResult ? runHealthChecks(auditResult) : []),
    [auditResult],
  );

  if (!auditResult) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <p className="text-muted-foreground">Loading...</p>
      </div>
    );
  }

  const { deduplication, cannibalization, incrementalROAS } = auditResult;
  const roasInflation = incrementalROAS.inflationRate;
  const roasDelta = incrementalROAS.reportedROAS - incrementalROAS.trueIncrementalROAS;

  return (
    <div className="flex flex-col min-h-screen">
      {/* Header */}
      <header className="sticky top-0 z-50 border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
        <div className="container mx-auto flex h-14 items-center justify-between px-4">
          <div className="flex items-center gap-3">
            <Link
              href="/upload"
              className={cn(buttonVariants({ variant: "ghost", size: "sm" }))}
            >
              <ArrowLeft className="h-4 w-4 mr-1" /> New Audit
            </Link>
            <span className="font-semibold">Audit Dashboard</span>
          </div>
          {auditResult.hasGSC ? (
            <Badge variant="default">Full Audit</Badge>
          ) : (
            <Badge variant="secondary">No GSC Data</Badge>
          )}
        </div>
      </header>

      <main className="flex-1 container mx-auto px-4 py-8">
        {/* KPI Cards */}
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4 mb-8">
          <KpiCard
            title="Reported ROAS"
            value={`${incrementalROAS.reportedROAS.toFixed(2)}x`}
            icon={<DollarSign className="h-4 w-4" />}
            sub={`Reported revenue: $${incrementalROAS.reportedRevenue.toLocaleString()}`}
          />
          <KpiCard
            title="True ROAS"
            value={`${incrementalROAS.trueIncrementalROAS.toFixed(2)}x`}
            icon={<Target className="h-4 w-4" />}
            sub={`Incremental revenue: $${incrementalROAS.incrementalRevenue.toLocaleString()}`}
            variant={roasDelta > 0.5 ? "warning" : "success"}
          />
          <KpiCard
            title="Inflation Rate"
            value={`${(roasInflation * 100).toFixed(0)}%`}
            icon={roasInflation > 0.3 ? <TrendingDown className="h-4 w-4" /> : <TrendingUp className="h-4 w-4" />}
            sub={`${roasDelta > 0 ? "Overstated by" : "Accurate"} ${Math.abs(roasDelta).toFixed(2)}x`}
            variant={roasInflation > 0.3 ? "critical" : roasInflation > 0.15 ? "warning" : "success"}
          />
          <KpiCard
            title="Duplication Rate"
            value={`${(deduplication.duplicationRate * 100).toFixed(0)}%`}
            icon={<BarChart3 className="h-4 w-4" />}
            sub={`${deduplication.platformReportedConversions} reported vs ${deduplication.actualConversions} actual`}
            variant={deduplication.duplicationRate > 0.15 ? "warning" : "success"}
          />
        </div>

        {/* Health Alerts */}
        {alerts.length > 0 && (
          <div className="mb-8 space-y-2">
            <h2 className="text-lg font-semibold flex items-center gap-2">
              <AlertTriangle className="h-4 w-4" /> Health Alerts
            </h2>
            {alerts.map((alert, i) => (
              <div
                key={i}
                className={`flex items-start gap-3 rounded-lg border p-3 text-sm ${
                  alert.severity === "critical"
                    ? "border-red-200 bg-red-50 text-red-800 dark:border-red-800 dark:bg-red-950 dark:text-red-200"
                    : alert.severity === "warning"
                    ? "border-yellow-200 bg-yellow-50 text-yellow-800 dark:border-yellow-800 dark:bg-yellow-950 dark:text-yellow-200"
                    : "border-blue-200 bg-blue-50 text-blue-800 dark:border-blue-800 dark:bg-blue-950 dark:text-blue-200"
                }`}
              >
                {alert.severity === "critical" ? (
                  <AlertTriangle className="h-4 w-4 mt-0.5 shrink-0" />
                ) : alert.severity === "warning" ? (
                  <AlertTriangle className="h-4 w-4 mt-0.5 shrink-0" />
                ) : (
                  <Info className="h-4 w-4 mt-0.5 shrink-0" />
                )}
                <div>
                  <p className="font-medium">{alert.title}</p>
                  <p>{alert.message}</p>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Charts */}
        <Tabs defaultValue="roas" className="mb-8">
          <TabsList>
            <TabsTrigger value="roas">ROAS Comparison</TabsTrigger>
            <TabsTrigger value="duplication">Duplication</TabsTrigger>
            <TabsTrigger value="cannibalization">Cannibalization</TabsTrigger>
            <TabsTrigger value="trends">Daily Trends</TabsTrigger>
          </TabsList>
          <TabsContent value="roas">
            <Card>
              <CardHeader>
                <CardTitle>Reported vs True Incremental ROAS</CardTitle>
                <CardDescription>
                  Platform-claimed revenue vs actual incremental revenue after removing organic baseline.
                </CardDescription>
              </CardHeader>
              <CardContent>
                <ROASChart result={auditResult} />
              </CardContent>
            </Card>
          </TabsContent>
          <TabsContent value="duplication">
            <Card>
              <CardHeader>
                <CardTitle>Conversion Duplication</CardTitle>
                <CardDescription>
                  Ad platform reported conversions vs verified Shopify orders per day.
                </CardDescription>
              </CardHeader>
              <CardContent>
                <DuplicationChart result={auditResult} />
              </CardContent>
            </Card>
          </TabsContent>
          <TabsContent value="cannibalization">
            <Card>
              <CardHeader>
                <CardTitle>Cannibalization Over Time</CardTitle>
                <CardDescription>
                  Days where both ad conversions and brand search exceed rolling averages — potential organic cannibalization.
                </CardDescription>
              </CardHeader>
              <CardContent>
                <CannibalizationChart result={auditResult} />
              </CardContent>
            </Card>
          </TabsContent>
          <TabsContent value="trends">
            <Card>
              <CardHeader>
                <CardTitle>Daily Spend vs Actual Conversions</CardTitle>
                <CardDescription>
                  Rolling correlation between ad spend and actual e-commerce sales.
                </CardDescription>
              </CardHeader>
              <CardContent>
                <TrendChart result={auditResult} />
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>

        {/* Summary Stats */}
        <Card>
          <CardHeader>
            <CardTitle>Detailed Metrics</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid gap-4 md:grid-cols-3 text-sm">
              <div>
                <p className="text-muted-foreground">Total Ad Spend</p>
                <p className="text-lg font-semibold">${incrementalROAS.totalSpend.toLocaleString()}</p>
              </div>
              <div>
                <p className="text-muted-foreground">Organic Baseline</p>
                <p className="text-lg font-semibold">
                  {auditResult.organicBaselineConversions.toFixed(1)} conversions/day
                </p>
              </div>
              <div>
                <p className="text-muted-foreground">Incremental Conversions</p>
                <p className="text-lg font-semibold">
                  {auditResult.incrementalConversionsPerDay.toFixed(1)}/day
                </p>
              </div>
              <div>
                <p className="text-muted-foreground">Spend-Conversion Correlation</p>
                <p className="text-lg font-semibold">
                  {auditResult.correlationMean.toFixed(3)}
                  {auditResult.correlationMean < 0.3 && auditResult.correlationMean > 0 && (
                    <Badge variant="secondary" className="ml-2">Weak</Badge>
                  )}
                  {auditResult.correlationMean <= 0 && (
                    <Badge variant="destructive" className="ml-2">Negative</Badge>
                  )}
                  {auditResult.correlationMean >= 0.3 && (
                    <Badge variant="default" className="ml-2">Moderate</Badge>
                  )}
                </p>
              </div>
              <div>
                <p className="text-muted-foreground">Cannibalization Score</p>
                <p className="text-lg font-semibold">
                  {(cannibalization.cannibalizationScore * 100).toFixed(0)}%
                  {!auditResult.hasGSC && (
                    <Badge variant="secondary" className="ml-2">No GSC</Badge>
                  )}
                </p>
              </div>
              <div>
                <p className="text-muted-foreground">Audit Period</p>
                <p className="text-lg font-semibold">
                  {auditResult.dailyRows.length} days
                  {" · "}
                  {auditResult.dailyRows[0]?.date} → {auditResult.dailyRows[auditResult.dailyRows.length - 1]?.date}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      </main>
    </div>
  );
}

function KpiCard({
  title,
  value,
  icon,
  sub,
  variant = "default",
}: {
  title: string;
  value: string;
  icon: React.ReactNode;
  sub: string;
  variant?: "default" | "success" | "warning" | "critical";
}) {
  const variantStyles = {
    default: "",
    success: "border-green-200 dark:border-green-800",
    warning: "border-yellow-200 dark:border-yellow-800",
    critical: "border-red-200 dark:border-red-800",
  };

  return (
    <Card className={variantStyles[variant]}>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm font-medium text-muted-foreground">{title}</CardTitle>
          {icon}
        </div>
        <CardDescription className="text-2xl font-bold text-foreground">{value}</CardDescription>
      </CardHeader>
      <CardContent>
        <p className="text-xs text-muted-foreground">{sub}</p>
      </CardContent>
    </Card>
  );
}
