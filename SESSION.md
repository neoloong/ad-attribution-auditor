# OpenCode Session Resume Prompt

Paste this into a new opencode session after `cd /Users/chao/ad-attribution-auditor` and running `/init`.

---

## Project: Ad Attribution Auditor

**Tagline:** "Don't let Big Tech grade their own homework."

An independent, open-source tool that audits ad platform attribution claims by cross-referencing Meta Ads and Google Ads reports against Shopify orders to calculate true incremental ROAS.

### Repos

- **Canonical:** https://github.com/neoloong/ad-attribution-auditor (Python + Next.js)
- **Live demo:** https://ad-attribution-auditor-next.vercel.app/dashboard?demo=true
- **Vercel project:** chaos-projects-6c35b5d4/ad-attribution-auditor-next

### Directory structure

```
/Users/chao/ad-attribution-auditor/
├── ad_audit/              # Python engine (70 tests, Streamlit UI)
├── pages/                  # Streamlit multi-page UI
├── tests/                  # pytest (70 tests)
├── data/                   # Sample CSVs
├── web/                    # Next.js 16 + TypeScript app
│   ├── src/lib/engine/     # Core audit algorithms (TS port)
│   ├── src/lib/ingestion/  # CSV parsing/normalization
│   ├── src/lib/store/      # Client-side state
│   ├── src/app/            # Routes: /, /upload, /dashboard, /report, /methodology
│   ├── src/components/ui/  # shadcn/ui
│   └── BLOG.md             # Ready-to-publish launch blog post
├── README.md               # Unified readme with both versions
├── bluepint.md             # Original product blueprint
└── app.py                  # Streamlit entry point
```

### Tech stack

- **Next.js version:** web/ — Next.js 16 (App Router), TypeScript, Tailwind CSS v4, shadcn/ui, Recharts, PapaParse, Lucide React
- **Python version:** ad_audit/ — Python 3.9+, Streamlit, Pandas, SciPy, Plotly, OpenAI SDK

### Core engine algorithms (already built, in both Python and TypeScript)

1. **Organic Baseline Estimation** — Three-tier: OLS regression (≥60 days), time-series interruption detection (≥7 consecutive zero-spend days), spend-off day average fallback
2. **De-duplication** — Daily min(reported, actual) overlap; duplication_rate = excess / platform_total
3. **Cannibalization Detection** — Rolling 30-day averages; flag days where both reported_conversions AND brand_clicks exceed their rolling means
4. **Incremental ROAS** — true_roas = (actual_revenue_on - organic_baseline_revenue) / total_spend; inflation_rate = (reported - true) / reported
5. **Health Check Alerts** — Configurable thresholds at critical/warning/info severity for duplication, inflation, cannibalization, correlation
6. **Rolling Pearson Correlation** — Vectorized rolling r between spend and actual_conversions

### What's deployed

- Live: https://ad-attribution-auditor-next.vercel.app
- All routes work: /, /upload, /dashboard, /dashboard?demo=true, /report, /methodology
- Build passes: 0 lint errors, TypeScript clean, 8 static routes
- One harmless SSR warning: "location is not defined" during prerender of /dashboard (from useRouter in client component)

---

## Immediate TODOs (Launch — this week)

### 1. Publish the blog post
- **File:** `web/BLOG.md` — fully written, ready to go
- **Step 1:** Create dev.to account at https://dev.to/enter (sign in with GitHub: neoloong)
- **Step 2:** Go to https://dev.to/new and paste the content of BLOG.md
- **Step 3:** Tags: `#opensource` `#typescript` `#nextjs` `#advertising` `#showdev`
- **Step 4:** Update all links to point to the CONSOLIDATED repo (github.com/neoloong/ad-attribution-auditor) not the old archived one
- **Step 5:** Publish

### 2. Post to Hacker News
- Go to https://news.ycombinator.com/submit
- **Title:** "Show HN: Ad Attribution Auditor — free tool that audits Meta/Google's ROAS claims"
- **URL:** https://ad-attribution-auditor-next.vercel.app
- **First comment:** Explain you're an applied scientist in ad measurement, built this because platforms inflate their numbers, open source (MIT), all processing in-browser, looking for feedback

### 3. Post to Reddit
Space these out over 24-48 hours after HN:

| Subreddit | Title |
|---|---|
| r/PPC | "I built a free tool that cross-references Meta/Google Ads against Shopify to find your true ROAS" |
| r/shopify | "Free tool to audit if Meta/Google are inflating your ad ROAS (open source)" |
| r/ecommerce | Same as r/shopify |
| r/SaaS | "Open source ad attribution auditor — built with Next.js, runs entirely in browser" |
| r/programming | Technical angle: "How I ported a Python attribution engine to TypeScript — OLS regression, rolling correlation, cannibalization scoring" |

---

## Short-term goals (1-2 months)

### Technical improvements
- Fix the harmless SSR "location is not defined" warning (add `export const dynamic = "force-dynamic"` without conflicting with `next/dynamic` import)
- Add user-level audit mode to Next.js (currently Python-only)
- Add search term wasted spend analysis to Next.js
- Add proper error boundaries and loading states
- Mobile responsive polish

### Growth
- Get 100+ GitHub stars
- Collect email list via a simple form on the landing page (no payment — just "get notified when Shopify App launches")
- Write 2-3 follow-up methodology blog posts:
  1. "The math behind organic baseline estimation"
  2. "Why cannibalization detection is the missing metric in ad measurement"
  3. "How to run your own incrementality test without spending $50k"
- Submit to Product Hunt

---

## Long-term goals (3-6 months)

### Phase 2: User acquisition
- Apply for Shopify App Store listing (free tier only — CSV upload)
- Add API connectors (Meta Marketing API, Google Ads API, Shopify Admin API) so users don't need CSV export
- Integrate LLM for AI-powered plain-English report summaries
- Build MCP server so users can query audit results in Claude/ChatGPT

### Phase 3: Monetization (after leaving Amazon)
- Paid tier: $29-49/mo for API auto-sync, AI reports, email alerts, multi-brand
- Enterprise: custom integrations, Data Clean Room, SLA
- Target: $15-30k MRR from 1-3% conversion of free Shopify App users

### Phase 4: Exit or scale
- $1M+ ARR → sell for $5-10M, or
- Raise VC, hire team, grow to $5M+ ARR

---

## Legal context (CRITICAL)

**You currently work at Amazon Ads.** Building a competing ad measurement product while employed creates IP assignment risk. The safe strategy:

- **NOW (at Amazon):** Keep everything open source (MIT), no LLC, no revenue, no customers, no Shopify App Store listing with your name, no Stripe. This is a "hobby open source project."
- **Blog posts:** Educational methodology content is safe. Don't write about Amazon's internal systems.
- **LATER (after leaving):** Form LLC, add Stripe, list on Shopify App Store, monetize.
- **Before going further:** Talk to an employment lawyer ($300-500 consult). Read your Amazon employment agreement's IP assignment and moonlighting clauses.

---

## Competitor landscape (for context)

| Player | Price | Target |
|---|---|---|
| Triple Whale | Free-$539/mo | SMB DTC |
| Northbeam | $1,500+/mo | Mid-market |
| Measured | $50k+/yr | Enterprise |
| Fospha | $50k+/yr | Enterprise |
| Wicked Reports | $499-999/mo | SMB |
| SegMetrics | $57-397/mo | Micro-SMB |
| Cometly | Usage-based | B2B SaaS |

**Market gap:** No product does proper causal measurement (MMM + incrementality) for under $500/mo. Brands spending $10-100k/mo on ads are underserved.

---

## Session commands cheat sheet

```bash
# Run Next.js dev server
cd /Users/chao/ad-attribution-auditor/web && npm run dev

# Run Python Streamlit app
cd /Users/chao/ad-attribution-auditor && streamlit run app.py

# Deploy to Vercel (auth required)
cd /Users/chao/ad-attribution-auditor/web && vercel --prod

# Run Python tests
cd /Users/chao/ad-attribution-auditor && python -m pytest tests/ -v

# Lint + typecheck Next.js
cd /Users/chao/ad-attribution-auditor/web && npm run lint && npm run build

# Git status
cd /Users/chao/ad-attribution-auditor && git status
```
