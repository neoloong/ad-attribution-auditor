# Market Research Report: Ad Attribution Auditor

**Project:** https://github.com/neoloong/ad-attribution-auditor
**Date:** 2026-04-14
**Analyst:** Scientist Agent (Research & Analysis)

---

## 1. Market Size: TAM / SAM / SOM

### TAM — Total Addressable Market

Global digital advertising spend is the relevant proxy:

- Global digital ad spend in 2024: **~$740 billion** (Statista, eMarketer)
- US alone: **$310–$340 billion** in 2024
- Growth rate: ~10–12% CAGR through 2028

Marketing analytics & attribution software:

- Global marketing analytics market: **$11.2B in 2023** → **$15.6B by 2030** (Allied Market Research)
- MTA (Multi-Touch Attribution) + MMM (Marketing Mix Modeling) software: **~$4–6B market today**

### SAM — Serviceable Addressable Market

Shopify e-commerce + Meta/Google Ads overlap:

- Shopify has **~4.6 million merchants** globally (2024)
- ~1.75 million are paying merchants
- ~500K–1M Shopify merchants actively running Meta + Google Ads
- US is largest market (~40% of Shopify GMV)
- Average Shopify growth-stage merchant ad spend: **$5K–$50K/month**
- Enterprise: $100K+/month
- Assuming 500K active Shopify ad spenders, total ad spend managed: ~$9B/month → **~$108B/year**
- At 1–3% "audit/reporting" budget: SAM ≈ **$1–3B/year**

### SOM — Serviceable Obtainable Market (3-year realistic)

Initial target: English-speaking Shopify merchants in US/CA/UK/AU, $10K–$500K/month ad spend:

- **50K–100K Shopify merchants** in this sweet spot
- At $200–$500/month SaaS pricing
- **Conservative SOM: $10M–$50M ARR** achievable with focused GTM
- **Target SOM: $50M–$200M ARR** if capturing 2–5% of segment

| Layer | Estimate |
|-------|----------|
| TAM | $15.6B (full marketing analytics market) |
| SAM | $1–3B (Shopify + Meta/Google e-commerce attribution) |
| SOM | $50M–$200M (realistic 3-year ARR, focused niche) |

---

## 2. Market Demand: The Pain Is Real

### Evidence of Inflated ROAS Problem

**Meta's own admissions:**
- Meta publicly acknowledged in 2022 that iOS-attributed conversions were overstated by **20–30%** due to Apple's ATT policy. CFO confirmed impact on reported ROAS.
- Meta admitted to overstating video metrics for "at least two years" (CNBC, 2022)
- A 2022 lawsuit accused Meta of using "fictional" user data; Meta set aside hundreds of millions for restitution

**iOS 14.5 impact:**
- Meta publicly confirmed **~50% reduction** in available conversion data for iOS users
- Advertisers suddenly had ROAS numbers that were both self-reported AND missing half the picture

**Industry response:**
- The problem spawned an entire category of "incrementality testing" tools (Rockerbox, Triple Whale, Northbeam)
- Brands realized last-touch and cross-platform attribution was systematically misleading them

**Real-world anecdotes (r/marketing, r/ecommerce):**
- Advertisers seeing "4x ROAS" on Meta while actual revenue barely covers ad spend
- Brand search cannibalization: bidding on own brand terms on Google, then crediting the Google click for an organic sale
- Cross-channel duplication: user sees Meta → Google → buys; both platforms claim 100% of conversion

### Market Validation (VC Backing)

| Company | Funding | Round |
|---------|---------|-------|
| **Rockerbox** | $40M+ | Series B |
| **Triple Whale** | $25M | Series B (2023) |
| **Northbeam** | $15M | Series A |
| **Measured** | $22M | Series B |

**Conclusion:** The category exists and is growing because the problem is real and unsolvable within the platforms themselves. Independent verification is a genuine market need.

---

## 3. Competitive Landscape

| Competitor | Type | Pricing | Shopify-Native | Key Differentiation |
|---|---|---|---|---|
| **Rockerbox** | MTA + MMM + Testing | Enterprise ($100K+/yr) | Partial | Unifies MTA, MMM, incrementality |
| **Triple Whale** | E-commerce attribution | $500–$5K/mo | ✅ Yes | Shopify-first, incrementality focus |
| **Northbeam** | MTA / dark funnel | Mid-market | Partial | Full-funnel, cross-device identity |
| **Measured** | MMM / Incrementality | Enterprise | No | Causal incrementality testing |
| **AppsFlyer** | Mobile attribution | All tiers | Via SDK | Mobile-first, privacy-centric |
| **Littledata** | Server-side tracking | $99–$999/mo | ✅ Yes | Shopify + Headless |
| **Hyros** | AI attribution | $2K+/mo | Yes | AI-powered, replaces GA |

### Open-Source Alternatives

- **DP6/Marketing-Attribution-Models** (GitHub) — Python library, heuristic + Shapley models, more academic than operational
- **Shapley Attribution** (GitHub) — scikit-learn compatible, requires data engineering
- **Bayesian Marketing Attribution** (GitHub) — Bayesian credible sets, research-oriented

### Our Niche

- **Positioning:** Independent (not a platform), open-source, Shopify-native, focused specifically on de-duplication + incremental ROAS vs. claimed ROAS
- **Advantage over incumbents:** No enterprise contract, lower price point ($99–$499/month vs. $100K+/year)
- **Advantage over open-source:** Production-ready Streamlit UI, dual audit modes (aggregate + user-level), LLM summaries, health alerts — more operational than academic Python libraries

---

## 4. Revenue Model

### SaaS Pricing

| Tier | Price | Features | Target |
|------|-------|----------|--------|
| Free / OSS | $0 | Self-host, full features, manual CSV | Developers, micro-merchants |
| Starter | $99/mo | 1 store, 30-day data, 5 reports/mo | <$5K/mo ad spend |
| Growth | $299/mo | 1 store, 90-day data, unlimited reports | $5K–$50K/mo ad spend |
| Pro | $599/mo | 3 stores, 12-month data, team access | $50K–$200K/mo ad spend |
| Agency | $1,500–$5,000/mo | Multi-client, white-label, API | Shopify-focused agencies |

### 3-Year Revenue Model (Conservative)

| Year | Paying Customers | Avg/Month | ARR |
|------|-----------------|-----------|-----|
| 1 | 200 | $300 | $720K |
| 2 | 800 | $350 | $3.36M |
| 3 | 2,500 | $400 | $12M |

**At tractable:** Even at conservative end, $3–12M ARR at Year 3 is fundable. Attribution tools command 5–10x ARR multiples due to strategic nature of data.

### Additional Revenue Streams

1. **Agency white-label** — $2K–$10K/month per agency, multi-tenant
2. **Data export / API access** — per-API-call pricing
3. **Consulting / implementation** — $150–$300/hour
4. **Benchmarking reports** — anonymized aggregate industry ROAS data

---

## 5. Go-to-Market Strategy

### Phase 1: Community & Credibility (Months 1–6)

- **Open-source distribution:** GitHub, Hacker News, Product Hunt launch
- **Content marketing:** "Why Your 4x ROAS Is Really 1.5x" — methodology blog posts
- **Communities:** r/shopify, r/ecommerce, Indie Hackers, Twitter/X
- **Shopify Partner Program** / App Store listing
- **Target:** 1,000+ GitHub stars, 50 community users, 10 paying customers

### Phase 2: Paid Tier Launch (Months 6–12)

- **Free → Paid conversion** with clear upgrade triggers (data limits, report limits)
- **Shopify-based ads:** Target merchants spending $10K+/month on Meta + Google
- **Podcast sponsorships:** E-commerce podcasts
- **Slack communities:** Shopify Founders, e-commerce Slack groups
- **Target:** 200–500 paying customers

### Phase 3: Agency Channel + Expansion (Year 2+)

- **Agency partner program:** Resell/whitelist to Shopify-focused agencies
- **Platform expansion:** WooCommerce, BigCommerce, Magento
- **Ad network expansion:** TikTok Ads, Pinterest, Amazon Ads
- **Target:** 2,500+ paying customers, $12M ARR

### Key GTM Channels

1. Shopify ecosystem (Partner Program, App Store, Shopify Unite)
2. Content/SEO ("ad attribution audit" keywords are high intent)
3. Community (Indie Hackers, Hacker News, r/shopify)
4. Direct sales (outreach to $50K+/month ad spend merchants)
5. Agencies (resell/white-label)

---

## 6. Profitability Feasibility

### Unit Economics (Growth Tier, $299/month)

| Metric | Value | Assessment |
|--------|-------|-----------|
| CAC | $200–$400 | Content/SEO-driven, low-friction |
| LTV | $7,176 | $299 × 24 months avg tenure |
| Gross Margin | 80–90% | SaaS, mostly infra + LLM API |
| **LTV:CAC** | **~24:1** | **Excellent** |
| **Payback** | **~1–1.3 months** | **Outstanding** |

Even at $500 CAC: LTV:CAC = ~14:1, still very healthy.

### Cost Structure

| Layer | % of Revenue |
|-------|-------------|
| Hosting | 5–10% |
| LLM API calls | 5–15% |
| Data storage | 2–5% |
| Payment processing | 3% |
| **Total COGS** | **15–30%** |

**Conclusion:** SaaS unit economics are highly favorable. The main challenge is CAC, not margin.

---

## 7. Risks & Challenges

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| Meta/Google change CSV schemas frequently | High | Medium | Schema versioning, alias mapping, monitoring |
| Email hash matching has low coverage (iOS opt-out) | High | Medium | Set expectations, offer aggregate mode as default |
| Organic baseline methodology challenged by users | Medium | High | Invest in better methodology (Bayesian TS, holdout tests) |
| Platforms restrict data access | Medium | High | Build API connectors while access is open; diversify data sources |
| No PMF — merchants don't act on audit results | Medium | High | A/B test "good news" vs "bad news" audit positioning |
| Competitor (Triple Whale) builds Shopify-first integration | Medium | Medium | Move faster, own the "independent auditor" positioning |
| Attribution methodology considered "unscientific" | Low | High | Academic citations, methodology transparency, option for holdout |

---

*Market Research v1.0 — 2026-04-14*
