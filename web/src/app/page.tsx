import Link from "next/link";
import { buttonVariants } from "@/components/ui/button";
import { Card, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { cn } from "@/lib/utils";
import { ArrowRight, BarChart3, FileSearch, Shield, Star, TrendingDown, Upload, Zap } from "lucide-react";

export default function LandingPage() {
  return (
    <div className="flex flex-col min-h-screen">
      {/* Navbar */}
      <header className="sticky top-0 z-50 border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60 shadow-[0_1px_3px_rgba(0,0,0,0.04)]">
        <div className="container mx-auto flex h-14 items-center justify-between px-4">
          <div className="flex items-center gap-2 font-bold text-lg">
            <FileSearch className="h-5 w-5" />
            <span className="font-heading">Ad Attribution Auditor</span>
          </div>
          <nav className="hidden md:flex items-center gap-6 text-sm text-muted-foreground">
            <a href="#features" className="hover:text-foreground transition-colors">Features</a>
            <a href="#how-it-works" className="hover:text-foreground transition-colors">How It Works</a>
            <Link href="/methodology" className="hover:text-foreground transition-colors">Methodology</Link>
            <a href="#open-source" className="hover:text-foreground transition-colors">Open Source</a>
          </nav>
          <div className="flex items-center gap-3">
            <Link
              href="/upload"
              className={cn(buttonVariants({ variant: "default", size: "sm" }))}
            >
              Get Started <ArrowRight className="ml-1 h-4 w-4" />
            </Link>
          </div>
        </div>
      </header>

      {/* Hero */}
      <section className="relative overflow-hidden py-28 md:py-36 bg-gradient-to-b from-muted/50 via-muted/20 to-background">
        <div className="absolute inset-0 bg-[image:radial-gradient(circle,rgba(0,0,0,0.04)_1px,transparent_1px)] bg-[size:24px_24px] [mask-image:radial-gradient(ellipse_at_center,black_30%,transparent_70%)]" />
        <div className="container mx-auto px-4 text-center relative">
          <Badge variant="secondary" className="mb-6">
            Open Source · MIT License
          </Badge>
          <h1 className="text-4xl font-bold tracking-tight sm:text-5xl md:text-6xl lg:text-7xl max-w-4xl mx-auto leading-tight bg-gradient-to-r from-primary to-chart-3 bg-clip-text text-transparent pb-1">
            Don&apos;t let Big Tech grade their own homework.
          </h1>
          <p className="mt-8 text-lg text-muted-foreground max-w-2xl mx-auto leading-relaxed">
            Independent ad attribution auditing. Cross-reference Meta Ads &amp; Google Ads
            against your Shopify orders to reveal your <strong>true incremental ROAS</strong>.
            Uncover over-counted conversions and cannibalized organic sales.
          </p>
          <div className="mt-10 flex flex-wrap items-center justify-center gap-4">
            <Link
              href="/upload"
              className={cn(buttonVariants({ size: "lg" }))}
            >
              Start Your Free Audit <ArrowRight className="ml-2 h-4 w-4" />
            </Link>
            <Link
              href="https://github.com/neoloong/ad-attribution-auditor"
              target="_blank"
              className={cn(buttonVariants({ variant: "outline", size: "lg" }))}
            >
              View on GitHub
            </Link>
          </div>
          <p className="mt-4 text-xs text-muted-foreground">
            Upload CSVs from Meta Ads, Google Ads, and Shopify — no API keys required.
          </p>
        </div>
      </section>

      <Separator />

      {/* Features */}
      <section id="features" className="py-20">
        <div className="container mx-auto px-4">
          <h2 className="text-3xl font-bold text-center mb-4">What This Tool Does</h2>
          <p className="text-center text-muted-foreground mb-12 max-w-xl mx-auto">
            Ad platforms self-report conversions and have every incentive to inflate
            the numbers. Your reported 4x ROAS might really be 1.5x.
          </p>
          <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
            <Card className="transition-all duration-300 hover:scale-[1.02] hover:shadow-md border-t-2 border-t-transparent hover:border-t-chart-1/40">
              <CardHeader>
                <div className="mb-3 flex h-12 w-12 items-center justify-center rounded-xl bg-gradient-to-br from-chart-1/25 to-chart-1/5">
                  <BarChart3 className="h-6 w-6 text-chart-1" />
                </div>
                <CardTitle>De-duplication</CardTitle>
                <CardDescription>
                  Identifies conversions over-counted across Meta and Google by comparing
                  platform claims to actual Shopify orders on the same day.
                </CardDescription>
              </CardHeader>
            </Card>
            <Card className="transition-all duration-300 hover:scale-[1.02] hover:shadow-md border-t-2 border-t-transparent hover:border-t-red-500/40">
              <CardHeader>
                <div className="mb-3 flex h-12 w-12 items-center justify-center rounded-xl bg-gradient-to-br from-red-500/25 to-red-500/5">
                  <TrendingDown className="h-6 w-6 text-red-500" />
                </div>
                <CardTitle>Cannibalization Detection</CardTitle>
                <CardDescription>
                  Finds users who were already searching for your brand — ad platforms
                  claim credit, but they would have purchased anyway.
                </CardDescription>
              </CardHeader>
            </Card>
            <Card className="transition-all duration-300 hover:scale-[1.02] hover:shadow-md border-t-2 border-t-transparent hover:border-t-green-500/40">
              <CardHeader>
                <div className="mb-3 flex h-12 w-12 items-center justify-center rounded-xl bg-gradient-to-br from-green-500/25 to-green-500/5">
                  <Zap className="h-6 w-6 text-green-500" />
                </div>
                <CardTitle>True Incremental ROAS</CardTitle>
                <CardDescription>
                  Real return on ad spend after removing inflated claims. Compare reported
                  ROAS vs what ad spend actually generated.
                </CardDescription>
              </CardHeader>
            </Card>
            <Card className="transition-all duration-300 hover:scale-[1.02] hover:shadow-md border-t-2 border-t-transparent hover:border-t-amber-500/40">
              <CardHeader>
                <div className="mb-3 flex h-12 w-12 items-center justify-center rounded-xl bg-gradient-to-br from-amber-500/25 to-amber-500/5">
                  <Shield className="h-6 w-6 text-amber-500" />
                </div>
                <CardTitle>Health Check Alerts</CardTitle>
                <CardDescription>
                  Automated warnings when duplication rate, ROAS inflation, or
                  cannibalization cross configurable thresholds.
                </CardDescription>
              </CardHeader>
            </Card>
            <Card className="transition-all duration-300 hover:scale-[1.02] hover:shadow-md border-t-2 border-t-transparent hover:border-t-blue-500/40">
              <CardHeader>
                <div className="mb-3 flex h-12 w-12 items-center justify-center rounded-xl bg-gradient-to-br from-blue-500/25 to-blue-500/5">
                  <FileSearch className="h-6 w-6 text-blue-500" />
                </div>
                <CardTitle>Search Term Analysis</CardTitle>
                <CardDescription>
                  Find high-spend keywords with zero verified purchases — cut the
                  wasted spend bleeding your budget.
                </CardDescription>
              </CardHeader>
            </Card>
            <Card className="transition-all duration-300 hover:scale-[1.02] hover:shadow-md border-t-2 border-t-transparent hover:border-t-purple-500/40">
              <CardHeader>
                <div className="mb-3 flex h-12 w-12 items-center justify-center rounded-xl bg-gradient-to-br from-purple-500/25 to-purple-500/5">
                  <Upload className="h-6 w-6 text-purple-500" />
                </div>
                <CardTitle>CSV Upload — No API Keys</CardTitle>
                <CardDescription>
                  Upload CSV exports from Meta Ads, Google Ads, and Shopify. Data
                  stays in your browser — no servers, no privacy risk.
                </CardDescription>
              </CardHeader>
            </Card>
          </div>
        </div>
      </section>

      {/* How It Works */}
      <section id="how-it-works" className="py-24 bg-muted/50">
        <div className="container mx-auto px-4">
          <h2 className="text-3xl font-bold text-center mb-16">How It Works</h2>
          <div className="relative max-w-4xl mx-auto px-4">
            <div className="hidden md:block absolute top-6 left-[12.5%] right-[12.5%] h-0.5 bg-gradient-to-r from-transparent via-primary/15 to-transparent" />
            <div className="grid gap-10 md:grid-cols-4">
              {[
                { step: "1", title: "Upload CSVs", desc: "Export reports from Meta Ads, Google Ads, and Shopify. Upload them in one click." },
                { step: "2", title: "Run Audit", desc: "Our engine cross-references daily spend, conversions, and revenue across all sources." },
                { step: "3", title: "View Dashboard", desc: "Interactive charts show your true ROAS, duplication rate, and cannibalization score." },
                { step: "4", title: "Take Action", desc: "Get alerts and recommendations to stop overpaying for non-incremental conversions." },
              ].map((item) => (
                <div key={item.step} className="text-center relative">
                  <div className="inline-flex h-14 w-14 items-center justify-center rounded-full bg-gradient-to-br from-primary to-chart-4 text-primary-foreground text-xl font-bold mb-4 z-10 relative">
                    {item.step}
                  </div>
                  <h3 className="font-semibold mb-2">{item.title}</h3>
                  <p className="text-sm text-muted-foreground">{item.desc}</p>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* Open Source */}
      <section id="open-source" className="py-24">
        <div className="container mx-auto px-4 max-w-2xl text-center">
          <h2 className="text-3xl font-bold mb-4">Free. Open Source. Forever.</h2>
          <p className="text-muted-foreground mb-10">
            No paid tiers, no waitlist, no &ldquo;request a demo.&rdquo; MIT licensed.
            All processing happens in your browser — your data never leaves your device.
            Built by someone who works in ad measurement and got tired of watching
            platforms inflate their numbers.
          </p>
          <div className="relative inline-flex">
            <div className="absolute -inset-4 bg-gradient-to-r from-primary/5 via-primary/10 to-primary/5 blur-xl rounded-full" />
            <div className="relative flex flex-wrap items-center justify-center gap-4">
              <Link
                href="/upload"
                className={cn(buttonVariants({ size: "lg" }))}
              >
                Try It Now <ArrowRight className="ml-2 h-4 w-4" />
              </Link>
              <a
                href="https://github.com/neoloong/ad-attribution-auditor"
                target="_blank"
                className={cn(buttonVariants({ variant: "outline", size: "lg" }))}
                rel="noreferrer"
              >
                <Star className="mr-1 h-4 w-4" /> Star on GitHub
              </a>
            </div>
          </div>
          <p className="mt-8 text-xs text-muted-foreground">
            Looking to contribute? PRs welcome. The core engine is 700 lines of typed, tested TypeScript.
          </p>
        </div>
      </section>

      {/* CTA */}
      <section className="py-20 bg-muted/50">
        <div className="container mx-auto px-4 text-center">
          <h2 className="text-3xl font-bold mb-4">Ready to see your true ROAS?</h2>
          <p className="text-muted-foreground mb-8 max-w-md mx-auto">
            Upload your CSV exports and get a free audit in under 2 minutes.
          </p>
          <Link
            href="/upload"
            className={cn(buttonVariants({ size: "lg" }))}
          >
            Start Your Free Audit <ArrowRight className="ml-2 h-4 w-4" />
          </Link>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t py-8 mt-auto">
        <div className="container mx-auto px-4 text-center text-sm text-muted-foreground">
          <p>Ad Attribution Auditor — Open Source (MIT). Built for DTC brands who want the truth.</p>
          <p className="mt-1 space-x-4">
            <a href="https://github.com/neoloong/ad-attribution-auditor" className="underline hover:text-foreground" target="_blank">
              GitHub
            </a>
            <Link href="/methodology" className="underline hover:text-foreground">Methodology</Link>
            <Link href="/upload" className="underline hover:text-foreground">Get Started</Link>
          </p>
        </div>
      </footer>
    </div>
  );
}
