"use client";

import { useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Button, buttonVariants } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { cn } from "@/lib/utils";
import { ArrowLeft, Trash2, Upload, Play, CheckCircle2, AlertCircle } from "lucide-react";
import {
  normalizeMetaAds,
  normalizeGoogleAds,
  normalizeShopifyOrders,
  normalizeGSC,
  mergeAdDaily,
} from "@/lib/ingestion/normalizer";
import { runAggregateAudit } from "@/lib/engine";
import { setStore } from "@/lib/store/audit-store";
import type { AdDaily, GSCDaily, ShopifyDaily } from "@/lib/ingestion/types";

interface FileState {
  name: string;
  content: string;
  parsed: AdDaily[] | ShopifyDaily[] | GSCDaily[];
  type: "meta" | "google" | "shopify" | "gsc";
}

export default function UploadPage() {
  const router = useRouter();
  const [files, setFiles] = useState<FileState[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [isRunning, setIsRunning] = useState(false);

  const handleFileUpload = useCallback(async (type: FileState["type"], fileList: FileList | null) => {
    if (!fileList?.length) return;
    setError(null);

    const file = fileList[0];
    const text = await file.text();

    try {
      let parsed: AdDaily[] | ShopifyDaily[] | GSCDaily[];
      switch (type) {
        case "meta":
          parsed = normalizeMetaAds(text);
          break;
        case "google":
          parsed = normalizeGoogleAds(text);
          break;
        case "shopify":
          parsed = normalizeShopifyOrders(text);
          break;
        case "gsc":
          parsed = normalizeGSC(text);
          break;
      }

      setFiles((prev) => {
        const filtered = prev.filter((f) => f.type !== type);
        return [...filtered, { name: file.name, content: text, parsed, type }];
      });
    } catch {
      setError(`Failed to parse ${file.name}. Check the CSV format.`);
    }
  }, []);

  const removeFile = (type: FileState["type"]) => {
    setFiles((prev) => prev.filter((f) => f.type !== type));
  };

  const getFileForType = (type: FileState["type"]) => files.find((f) => f.type === type);

  const canRun = files.some((f) => (f.type === "meta" || f.type === "google")) && files.some((f) => f.type === "shopify");

  const runAudit = () => {
    setIsRunning(true);
    setError(null);

    try {
      const meta = files.find((f) => f.type === "meta")?.parsed as AdDaily[] | undefined;
      const google = files.find((f) => f.type === "google")?.parsed as AdDaily[] | undefined;
      const shopify = files.find((f) => f.type === "shopify")?.parsed as ShopifyDaily[] | undefined;
      const gsc = files.find((f) => f.type === "gsc")?.parsed as GSCDaily[] | undefined;

      if (!shopify || !shopify.length) {
        setError("Shopify orders are required.");
        setIsRunning(false);
        return;
      }

      const adDaily: AdDaily[] = [];
      if (meta) adDaily.push(...meta);
      if (google) adDaily.push(...google);

      if (!adDaily.length) {
        setError("At least one ad platform (Meta or Google) is required.");
        setIsRunning(false);
        return;
      }

      const mergedAdDaily = mergeAdDaily(meta || [], google || []);

      const result = runAggregateAudit(
        mergedAdDaily,
        shopify,
        gsc,
      );

      setStore({
        uploadedFiles: {
          metaAds: meta || null,
          googleAds: google || null,
          shopifyOrders: shopify || null,
          gscBrandSearch: gsc || null,
        },
        auditResult: result,
        isRunning: false,
        error: null,
      });

      router.push("/dashboard");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Audit failed. Check your data.");
      setIsRunning(false);
    }
  };

  const fileConfigs = [
    { type: "meta" as const, label: "Meta Ads CSV", desc: "Exported from Meta Ads Manager. Requires Day, Campaign name, Amount spent (USD), Purchases.", accept: ".csv" },
    { type: "google" as const, label: "Google Ads CSV", desc: "Exported from Google Ads. Requires Day, Campaign, Cost, Conversions.", accept: ".csv" },
    { type: "shopify" as const, label: "Shopify Orders CSV", desc: "Exported from Shopify admin. Requires Name, Email, Created at, Total.", accept: ".csv", required: true },
    { type: "gsc" as const, label: "Google Search Console CSV", desc: "Brand search data. Requires Date, Top queries, Clicks. Optional — enables cannibalization detection.", accept: ".csv", optional: true },
  ];

  return (
    <div className="flex flex-col min-h-screen">
      <header className="sticky top-0 z-50 border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
        <div className="container mx-auto flex h-14 items-center px-4">
          <Link
            href="/"
            className={cn(buttonVariants({ variant: "ghost", size: "sm" }), "mr-2")}
          >
            <ArrowLeft className="h-4 w-4 mr-1" /> Home
          </Link>
          <span className="font-semibold">Upload Data</span>
        </div>
      </header>

      <main className="flex-1 container mx-auto px-4 py-8 max-w-2xl">
        <div className="mb-8">
          <h1 className="text-2xl font-bold mb-2">Upload Your Ad & Sales Data</h1>
          <p className="text-muted-foreground text-sm">
            Export CSV reports from your ad platforms and Shopify, then upload them here.
            All processing happens in your browser — your data never leaves your device.
          </p>
        </div>

        <div className="space-y-4">
          {fileConfigs.map((cfg) => {
            const file = getFileForType(cfg.type);
            return (
              <Card key={cfg.type} className={cfg.required ? "border-primary/50" : ""}>
                <CardHeader className="pb-2">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <CardTitle className="text-base">{cfg.label}</CardTitle>
                      {cfg.required && <Badge variant="default">Required</Badge>}
                      {cfg.optional && <Badge variant="secondary">Optional</Badge>}
                    </div>
                    {file && (
                      <Button variant="ghost" size="icon" onClick={() => removeFile(cfg.type)}>
                        <Trash2 className="h-4 w-4 text-muted-foreground" />
                      </Button>
                    )}
                  </div>
                  <CardDescription className="text-xs">{cfg.desc}</CardDescription>
                </CardHeader>
                <CardContent>
                  {file ? (
                    <div className="flex items-center gap-2 text-sm text-green-600">
                      <CheckCircle2 className="h-4 w-4" />
                      <span className="truncate">{file.name}</span>
                      <span className="text-muted-foreground text-xs">
                        ({file.parsed.length} days)
                      </span>
                    </div>
                  ) : (
                    <label className="flex items-center gap-2 cursor-pointer text-sm text-muted-foreground hover:text-foreground transition-colors">
                      <Upload className="h-4 w-4" />
                      <span>Choose CSV file</span>
                      <input
                        type="file"
                        accept={cfg.accept}
                        className="hidden"
                        onChange={(e) => handleFileUpload(cfg.type, e.target.files)}
                      />
                    </label>
                  )}
                </CardContent>
              </Card>
            );
          })}
        </div>

        {error && (
          <div className="mt-4 flex items-center gap-2 text-sm text-destructive">
            <AlertCircle className="h-4 w-4" />
            {error}
          </div>
        )}

        <Button
          className="mt-8 w-full"
          size="lg"
          disabled={!canRun || isRunning}
          onClick={runAudit}
        >
          {isRunning ? (
            <>Running Audit...</>
          ) : (
            <><Play className="mr-2 h-4 w-4" /> Run Audit</>
          )}
        </Button>

        <Separator className="my-8" />

        <div className="text-center text-sm text-muted-foreground">
          <p>No data? Try our <Link href="/dashboard?demo=true" className="underline hover:text-foreground">demo dashboard</Link> with sample data.</p>
        </div>
      </main>
    </div>
  );
}
