import Link from "next/link";
import { buttonVariants } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import { Separator } from "@/components/ui/separator";
import { ArrowLeft, BarChart3, TrendingDown, Zap, Shield, Brain, LineChart } from "lucide-react";

export default function MethodologyPage() {
  return (
    <div className="flex flex-col min-h-screen">
      <header className="sticky top-0 z-50 border-b bg-background/95 backdrop-blur">
        <div className="container mx-auto flex h-14 items-center px-4">
          <Link href="/" className={cn(buttonVariants({ variant: "ghost", size: "sm" }), "mr-2")}>
            <ArrowLeft className="h-4 w-4 mr-1" /> Home
          </Link>
          <span className="font-semibold">Methodology</span>
        </div>
      </header>

      <main className="flex-1 container mx-auto px-4 py-8 max-w-3xl">
        <h1 className="text-3xl font-bold mb-2">How the Audit Works</h1>
        <p className="text-muted-foreground mb-8">
          A technical deep-dive into the algorithms behind the Ad Attribution Auditor.
          All processing happens client-side; no data leaves your browser.
        </p>

        {/* TOC */}
        <nav className="mb-12 p-4 rounded-lg bg-muted text-sm space-y-1">
          <p className="font-medium mb-2">Contents</p>
          <a href="#organic-baseline" className="block text-muted-foreground hover:text-foreground transition-colors">
            Organic Baseline Estimation
          </a>
          <a href="#deduplication" className="block text-muted-foreground hover:text-foreground transition-colors">
            De-duplication
          </a>
          <a href="#cannibalization" className="block text-muted-foreground hover:text-foreground transition-colors">
            Cannibalization Detection
          </a>
          <a href="#incremental-roas" className="block text-muted-foreground hover:text-foreground transition-colors">
            Incremental ROAS Computation
          </a>
          <a href="#correlation" className="block text-muted-foreground hover:text-foreground transition-colors">
            Spend-Conversion Correlation
          </a>
          <a href="#health-checks" className="block text-muted-foreground hover:text-foreground transition-colors">
            Health Check Alerts
          </a>
          <a href="#limitations" className="block text-muted-foreground hover:text-foreground transition-colors">
            Limitations &amp; Assumptions
          </a>
        </nav>

        {/* Section: Organic Baseline */}
        <section id="organic-baseline" className="mb-12">
          <h2 className="text-2xl font-bold mb-4 flex items-center gap-2">
            <Brain className="h-5 w-5" /> Organic Baseline Estimation
          </h2>
          <p className="mb-4">
            The fundamental question in ad measurement is: <em>how many conversions would
            have happened without any ads?</em> This is the <strong>organic baseline</strong> &mdash;
            the daily conversion rate driven by brand recognition, word-of-mouth, and
            organic search, not by paid media.
          </p>
          <p className="mb-4">
            We estimate the organic baseline using a three-tier decision tree, falling
            back to simpler methods when data is insufficient for more rigorous approaches.
          </p>

          <Card className="mb-4">
            <CardHeader>
              <CardTitle className="text-lg">Tier 1: OLS Linear Regression</CardTitle>
              <CardDescription>Requires &ge; 60 days of data with spend variation</CardDescription>
            </CardHeader>
            <CardContent className="space-y-2 text-sm">
              <p>
                We fit a simple linear model:
              </p>
              <div className="bg-muted p-3 rounded font-mono text-sm my-2 overflow-x-auto">
                actual_conversions = &beta;<sub>0</sub> + &beta;<sub>1</sub> &times; spend + &epsilon;
              </div>
              <p>
                The intercept &beta;<sub>0</sub> is the estimated daily conversion count when
                spend = $0 &mdash; that is, the organic baseline. Using ordinary least squares
                via the normal equations:
              </p>
              <div className="bg-muted p-3 rounded font-mono text-sm my-2 overflow-x-auto">
                &beta; = (X<sup>T</sup>X)<sup>-1</sup>X<sup>T</sup>y
              </div>
              <p>Requirements for this method to be used:</p>
              <ul className="list-disc list-inside space-y-1 ml-2">
                <li>At least 60 days of data</li>
                <li>Spend standard deviation &ge; $1.00 (meaningful variation)</li>
                <li>At least 3 zero-spend days (to anchor the intercept)</li>
                <li>Positive intercept (organic baseline cannot be negative)</li>
                <li>R&sup2; &ge; 0.01 (model explains at least some variance)</li>
              </ul>
            </CardContent>
          </Card>

          <Card className="mb-4">
            <CardHeader>
              <CardTitle className="text-lg">Tier 2: Time-Series Interruption Detection</CardTitle>
              <CardDescription>Fallback when regression conditions are not met</CardDescription>
            </CardHeader>
            <CardContent className="space-y-2 text-sm">
              <p>
                We scan the daily timeline for sustained periods (7+ consecutive days) with
                no ad spend. The average daily conversions during the longest such
                interruption serves as the organic baseline.
              </p>
              <p>
                This is a <strong>natural experiment</strong>: if you stop advertising
                for a week, whatever sales still come in are organic. The longer the
                interruption, the more reliable the estimate.
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Tier 3: Spend-Off Day Average</CardTitle>
              <CardDescription>Simplest fallback</CardDescription>
            </CardHeader>
            <CardContent className="text-sm">
              <p>
                If no qualifying interruption is found, we take the mean daily conversions
                on all days where spend is below the threshold ($5 by default). This is
                the least reliable method and is only used as a last resort.
              </p>
            </CardContent>
          </Card>
        </section>

        <Separator className="mb-12" />

        {/* Section: De-duplication */}
        <section id="deduplication" className="mb-12">
          <h2 className="text-2xl font-bold mb-4 flex items-center gap-2">
            <BarChart3 className="h-5 w-5" /> De-duplication
          </h2>
          <p className="mb-4">
            Ad platforms self-report conversions, and they have every incentive to
            inflate the numbers. We cross-reference platform claims against your actual
            Shopify orders to measure the gap.
          </p>

          <h3 className="font-semibold mb-2">Algorithm</h3>
          <p className="mb-2 text-sm">For each day in the audit period:</p>
          <div className="bg-muted p-3 rounded font-mono text-sm my-2 overflow-x-auto">
            daily_overlap = min(reported_conversions, actual_conversions)<br />
            excess = max(0, platform_total - actual_total)<br />
            duplication_rate = excess / platform_total
          </div>
          <p className="text-sm">
            The <strong>duplication rate</strong> answers: what fraction of ad platform-claimed
            conversions have no matching Shopify order on the same day? A rate of 30%
            means nearly a third of &ldquo;conversions&rdquo; may be fabricated or double-counted.
          </p>
        </section>

        <Separator className="mb-12" />

        {/* Section: Cannibalization */}
        <section id="cannibalization" className="mb-12">
          <h2 className="text-2xl font-bold mb-4 flex items-center gap-2">
            <TrendingDown className="h-5 w-5" /> Cannibalization Detection
          </h2>
          <p className="mb-4">
            Not all ad conversions are incremental. Some users were already going to
            buy &mdash; they searched for your brand before clicking your ad. The ad
            platform claims credit, but the purchase was organic.
          </p>
          <p className="mb-4">
            This is <strong>cannibalization</strong>: paid media eating organic demand.
          </p>

          <h3 className="font-semibold mb-2">Algorithm</h3>
          <p className="mb-2 text-sm">
            We compute rolling averages over a configurable window (default 30 days)
            for both reported conversions and brand search clicks:
          </p>
          <div className="bg-muted p-3 rounded font-mono text-sm my-2 overflow-x-auto">
            meta_rolling_avg(t) = mean(reported_conversions[t-window : t])<br />
            brand_rolling_avg(t) = mean(brand_clicks[t-window : t])
          </div>
          <p className="mb-2 text-sm">
            A day is flagged as <strong>cannibalized</strong> when <em>both</em> conditions are true:
          </p>
          <ol className="list-decimal list-inside text-sm ml-2 space-y-1">
            <li>Ad-reported conversions exceed their rolling average</li>
            <li>Brand search clicks exceed their rolling average</li>
            <li>Ad spend is above the threshold (active advertising)</li>
          </ol>
          <p className="mt-2 text-sm">
            The intuition: if you&apos;re advertising heavily AND people are searching for
            your brand organically at the same time, the ads are likely taking credit for
            demand that already existed. This requires Google Search Console data to be
            uploaded.
          </p>

          <h3 className="font-semibold mb-2 mt-4">Cannibalization Score</h3>
          <div className="bg-muted p-3 rounded font-mono text-sm my-2 overflow-x-auto">
            cannibalization_score = cannibalized_days / total_spend_on_days<br />
            cannibalized_revenue_fraction = cannibalized_revenue / spend_on_revenue
          </div>
          <p className="text-sm">
            The score is the fraction of active-advertising days that show this pattern.
            The revenue fraction shows what portion of ad-attributed revenue falls on
            these days.
          </p>
        </section>

        <Separator className="mb-12" />

        {/* Section: Incremental ROAS */}
        <section id="incremental-roas" className="mb-12">
          <h2 className="text-2xl font-bold mb-4 flex items-center gap-2">
            <Zap className="h-5 w-5" /> Incremental ROAS Computation
          </h2>
          <p className="mb-4">
            Return on Ad Spend (ROAS) is the most-watched metric in ad buying. But the
            number your dashboard shows is <strong>reported ROAS</strong> &mdash; it assumes
            every conversion on an ad day was caused by the ad. We compute the
            <strong> true incremental ROAS</strong> instead.
          </p>

          <h3 className="font-semibold mb-2">Algorithm</h3>
          <div className="bg-muted p-3 rounded font-mono text-sm my-2 overflow-x-auto">
            reported_roas = reported_revenue / total_spend<br />
            avg_rev_per_conv = total_actual_revenue / total_actual_conversions<br />
            organic_revenue = organic_baseline &times; avg_rev_per_conv &times; spend_on_days<br />
            incremental_revenue = max(0, actual_revenue_on - organic_revenue)<br />
            true_incremental_roas = incremental_revenue / total_spend<br />
            inflation_rate = (reported_roas - true_roas) / reported_roas
          </div>
          <p className="mt-2 text-sm">
            If your dashboard shows a 4.0x ROAS but your true incremental ROAS is 1.5x,
            the inflation rate is 62.5%. Nearly two-thirds of your &ldquo;return&rdquo; may be revenue
            that would have come in anyway.
          </p>
        </section>

        <Separator className="mb-12" />

        {/* Section: Correlation */}
        <section id="correlation" className="mb-12">
          <h2 className="text-2xl font-bold mb-4 flex items-center gap-2">
            <LineChart className="h-5 w-5" /> Spend-Conversion Correlation
          </h2>
          <p className="mb-4">
            A simple but powerful test: does spending more actually correlate with more
            verified purchases? We compute Pearson&apos;s r on a rolling window to measure
            the relationship over time.
          </p>
          <div className="bg-muted p-3 rounded font-mono text-sm my-2 overflow-x-auto">
            r = Cov(spend, actual_conversions) / (&sigma;<sub>spend</sub> &times; &sigma;<sub>conv</sub>)
          </div>
          <p className="text-sm">
            A negative or near-zero correlation is a red flag: your ad spend has little
            to no detectable relationship with actual sales. A strong positive correlation
            (&ge; 0.5) suggests spend is driving real incremental conversions.
          </p>
        </section>

        <Separator className="mb-12" />

        {/* Section: Health Checks */}
        <section id="health-checks" className="mb-12">
          <h2 className="text-2xl font-bold mb-4 flex items-center gap-2">
            <Shield className="h-5 w-5" /> Health Check Alerts
          </h2>
          <p className="mb-4">
            We evaluate all computed metrics against configurable thresholds and surface
            alerts at three severity levels. These are designed to catch problems before
            they burn through your budget.
          </p>

          <div className="overflow-x-auto text-sm">
            <table className="w-full border-collapse">
              <thead>
                <tr className="border-b">
                  <th className="text-left py-2 pr-4">Metric</th>
                  <th className="text-left py-2 pr-4">Warning</th>
                  <th className="text-left py-2">Critical</th>
                </tr>
              </thead>
              <tbody>
                <tr className="border-b">
                  <td className="py-2 pr-4">Duplication Rate</td>
                  <td className="py-2 pr-4">&ge; 15%</td>
                  <td className="py-2">&ge; 30%</td>
                </tr>
                <tr className="border-b">
                  <td className="py-2 pr-4">ROAS Inflation</td>
                  <td className="py-2 pr-4">&ge; 30%</td>
                  <td className="py-2">&ge; 60%</td>
                </tr>
                <tr className="border-b">
                  <td className="py-2 pr-4">Cannibalization Score</td>
                  <td className="py-2 pr-4">&ge; 20%</td>
                  <td className="py-2">&ge; 40%</td>
                </tr>
                <tr className="border-b">
                  <td className="py-2 pr-4">S-C Correlation</td>
                  <td className="py-2 pr-4">&le; 0.3</td>
                  <td className="py-2">&le; 0.0 (negative)</td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>

        <Separator className="mb-12" />

        {/* Section: Limitations */}
        <section id="limitations" className="mb-12">
          <h2 className="text-2xl font-bold mb-4">Limitations &amp; Assumptions</h2>
          <Card>
            <CardContent className="space-y-3 text-sm pt-6">
              <div>
                <h3 className="font-semibold mb-1">Not a true controlled experiment</h3>
                <p>
                  This tool uses observational data, not randomized controlled trials.
                  The organic baseline estimate is correlational, not causal. For rigorous
                  incrementality measurement, run geo-experiments or audience-split tests.
                </p>
              </div>
              <div>
                <h3 className="font-semibold mb-1">Same-day attribution only</h3>
                <p>
                  We compare ad platform data and Shopify orders on the same calendar day.
                  This does not account for delayed conversions (ads seen on Monday,
                  purchase on Friday). For a more complete picture, a multi-touch or
                  time-decay model would be needed.
                </p>
              </div>
              <div>
                <h3 className="font-semibold mb-1">No cross-device tracking</h3>
                <p>
                  A user who clicks an ad on mobile but purchases on desktop may not be
                  matched. This is a fundamental limitation of browser-based measurement.
                </p>
              </div>
              <div>
                <h3 className="font-semibold mb-1">Minimum data requirements</h3>
                <p>
                  For the most reliable organic baseline (OLS regression), we need at
                  least 60 days of data with meaningful spend variation and some zero-spend
                  days. Shorter periods or stable-spend patterns will fall back to less
                  rigorous estimation methods.
                </p>
              </div>
              <div>
                <h3 className="font-semibold mb-1">Platform reporting bias</h3>
                <p>
                  We accept ad platform CSV exports at face value for &ldquo;reported&rdquo; metrics.
                  If a platform under-reports spend or over-reports conversions in their
                  export (unlikely but possible), our comparison will be affected.
                </p>
              </div>
            </CardContent>
          </Card>
        </section>

        <Separator className="mb-12" />

        <section className="mb-12">
          <h2 className="text-2xl font-bold mb-4">Privacy</h2>
          <p className="mb-4">
            All processing happens <strong>entirely in your browser</strong>. Your CSV data
            never leaves your device. No API calls, no servers, no analytics tracking. We
            use WebAssembly-free JavaScript: the audit engine runs in the main thread using
            typed arrays for performance. View the source at{" "}
            <a href="https://github.com/neoloong/ad-attribution-auditor" className="underline" target="_blank">
              github.com/neoloong/ad-attribution-auditor
            </a>
            {" "}(Python Streamlit version) or the Next.js port at{" "}
            <a href="https://github.com/neoloong/ad-attribution-auditor-next" className="underline" target="_blank">
              the Next.js repo
            </a>.
          </p>
        </section>
      </main>
    </div>
  );
}
