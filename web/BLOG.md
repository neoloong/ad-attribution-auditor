# I Built a Free Tool That Exposes How Much Meta and Google Inflate Your ROAS

**Or: Don't let Big Tech grade their own homework.**

---

If you run ads for a DTC brand, you've felt it. Meta Ads Manager says you have a 4.2x ROAS. Google Ads says 3.8x. Shopify says you made $12,000 this month. The math doesn't add up — but you can't prove it, because every platform claims the same order as "their" conversion.

I work in ad measurement. I see how the sausage is made. So I built a tool that cross-references your ad platform CSV exports against your actual Shopify orders and tells you what's real.

It's free. It's open source. It runs entirely in your browser — no data leaves your device.

## What the tool does

You upload three (or four) CSV files:

- **Meta Ads export** (Day, Campaign, Spend, Purchases)
- **Google Ads export** (Day, Campaign, Cost, Conversions)  
- **Shopify Orders export** (Name, Email, Created at, Total)
- **Google Search Console** (optional — enables cannibalization detection)

It runs three analyses:

### 1. De-duplication
How many "conversions" do ad platforms report vs how many actual Shopify orders exist? The tool compares day-by-day and calculates a duplication rate. I've seen rates over 40% — meaning nearly half of reported conversions have no matching purchase.

### 2. Cannibalization Detection
This is the one nobody talks about. A user searches for your brand on Google (organic intent), then clicks your Meta ad later. Meta claims the conversion. But they were buying anyway.

The tool computes rolling averages of brand search clicks and ad conversions over 30 days. When *both* spike above their averages on the same day, it's flagged as cannibalized — paid media eating organic demand.

### 3. True Incremental ROAS
The standard ROAS formula (revenue / spend) assumes every conversion on ad days was caused by ads. We compute what would have happened without ads using three methods:

- **OLS regression** (≥60 days): actual_conversions = β₀ + β₁ × spend. The intercept β₀ is your organic baseline.
- **Time-series interruption** (≥7 consecutive zero-spend days): natural experiment — what happened when ads were off?
- **Spend-off day average** (fallback): mean conversions on days below $5 spend.

True incremental revenue = actual revenue on ad days − organic baseline revenue. Divide by spend, and you get what your ads actually generated.

## The numbers are sobering

Running the tool on synthetic data modeled after real patterns:

| Metric | Platform Says | Reality |
|--------|--------------|---------|
| ROAS | 4.2x | 1.5x |
| Inflation | — | 64% |
| Duplication | — | ~30% |
| Cannibalized days | — | ~25% |

That 4.2x ROAS you're reporting to your team? Nearly two-thirds of that revenue was coming in anyway.

## Why I built this

I work in ad measurement at a major tech company. The internal models are sophisticated, but the public-facing numbers — the ones in your dashboard — are designed to make you spend more. Every platform grades its own homework.

The sub-$500/month measurement market is nearly empty. Northbeam starts at $1,500/month. Triple Whale's advanced tier is $259/month but their actual incrementality features are in the $539+ tier. Measured and Fospha are $50k+/year enterprise deals.

There are hundreds of thousands of DTC brands spending $10-100k/month on ads who have no access to rigorous measurement. This tool is for them.

## Try it

**Live demo (no upload needed):** [Dashboard with sample data](https://github.com/neoloong/ad-attribution-auditor-next?demo=true)

**Run it locally:**
```bash
git clone https://github.com/neoloong/ad-attribution-auditor.git
cd ad-attribution-auditor/web
npm install
npm run dev
```

**Full methodology:** [How the audit works](https://ad-attribution-auditor-next.vercel.app/methodology)

---

Built with Next.js, TypeScript, Recharts, and shadcn/ui. All computation runs client-side using typed arrays — zero dependencies on external services.

MIT licensed. Star the repo if you find it useful. PRs welcome.

*[Originally published on [dev.to/neoloong](https://dev.to/neoloong)]*
