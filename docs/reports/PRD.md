# PRD: Ad Attribution Auditor

**Project:** https://github.com/neoloong/ad-attribution-auditor
**Date:** 2026-04-15
**Author:** PM Agent
**Version:** 1.1 — Chrome Extension Strategy Added

---

## 1. Problem Statement & Vision

### The Problem

Ad platforms (Meta, Google) self-report conversions. They have every structural incentive to inflate numbers:

- **Cross-channel double-counting**: A user sees a Meta ad, then a Google ad, then buys — both platforms count 100% of the conversion.
- **Non-incremental attribution**: A user who was already going to buy (already searching for the brand) gets counted as a "conversion" by every platform that touched them.
- **iOS 14.5 collapse**: Apple's ATT policy reduced Meta's conversion data by ~50%, and Meta publicly acknowledged ROAS overstatement of 20–30%.

Your reported 4x ROAS might really be 1.5x. You're making budget decisions based on platform-inflated data.

### Vision

*"Don't let Big Tech grade their own homework."*

Use Shopify orders — the actual ground truth of what was purchased — to independently verify what Meta and Google are claiming. Build a tool that cuts through the self-serving attribution noise and tells merchants: "Here is what your ads actually drove."

---

## 2. Product Architecture: Two Products, One Moat

We are building **two products** that share the same core audit engine:

| Product | Type | Target User | Entry Point |
|---------|------|-------------|-------------|
| **Ad Audit Chrome Extension** | Browser extension | Any merchant viewing ad dashboards | Zero-friction, viral |
| **Ad Audit Web App** | SaaS (Streamlit) | Merchants wanting deep analysis + recurring audits | Power users, agencies |

**The core audit engine is the same.** The Chrome Extension is the lightweight, always-there entry point. The Web App is the full-featured power tool.

### Why Both?

- **Chrome Extension** = distribution + recurring revenue + daily utility
- **Web App** = depth + trust + agency upsell + data persistence
- **Together** = network effect (extension users feed data to improve benchmarks)

---

## 3. Chrome Extension: The Primary Product

### What It Is

A Chrome browser extension that analyzes ad attribution in real-time as the user browses their Meta Ads Manager or Google Ads dashboard. It reads the data already on the page, runs it against the audit engine, and displays an "Attribution Accuracy Score" overlay.

**It does NOT require CSV uploads.** It works automatically when you visit your ad dashboards.

---

### How It Works: Step-by-Step Usage Flow

#### Setup (One-Time, 2 Minutes)

1. Install extension from Chrome Web Store
2. Click extension icon → "Connect Your Store"
3. Paste your Shopify store URL
4. Paste your Shopify Admin API key + secret (created in Shopify Partners dashboard)
5. Extension tests connection → shows "Connected ✅"
6. Done. No CSV, no manual uploads, no configuration.

#### Daily Usage: Meta Ads Dashboard

**Scenario:** A performance marketer opens their Meta Ads Manager at `business.facebook.com/ads_manager` and is looking at a campaign report.

**What the extension does automatically:**

1. **Detects** the page is a Meta Ads report (via URL + DOM inspection)
2. **Reads** the campaign table data (campaign name, impressions, clicks, spend, reported conversions, reported ROAS)
3. **Queries Shopify** via API for actual orders in the same date range
4. **Runs the audit engine** locally in the browser:
   - De-duplicates cross-platform conversions
   - Removes brand-search cannibalization (orders where customer searched brand on Google before purchasing)
   - Calculates true incremental ROAS
5. **Overlays the results** on the page as a floating scorecard:

```
┌─────────────────────────────────────────────────────┐
│ 🔍 Ad Audit Extension                    [Expanded ▼]│
├─────────────────────────────────────────────────────┤
│  Campaign: Summer Sale - Retargeting                │
│                                                     │
│  Meta Reported          True (Shopify)    Inflation │
│  ─────────────          ──────────────    ─────────  │
│  Conversions: 847   →   512              +39.5%  🔴│
│  ROAS: 4.2x         →   2.1x             -50%   🔴│
│  Spend: $12,400     →   [same]                  ⚪  │
│                                                     │
│  💡 De-dupe: 198 conversions counted by both       │
│     Meta & Google were removed                     │
│  💡 Cannibalization: 137 orders had prior brand    │
│     Google searches (organic anyway)               │
│                                                     │
│  [View Full Report]  [Export PDF]                  │
└─────────────────────────────────────────────────────┘
```

6. **User clicks "View Full Report"** → opens Web App with full audit details

#### Daily Usage: Google Ads Dashboard

Same flow at `ads.google.com`:

```
┌─────────────────────────────────────────────────────┐
│ 🔍 Ad Audit Extension                               │
├─────────────────────────────────────────────────────┤
│  Google Reported     True (Shopify)     Inflation   │
│  ──────────────      ──────────────     ─────────   │
│  Conversions: 623   →   389             +37.7%  🔴│
│  ROAS: 3.8x        →   1.9x             -50%    🔴│
│                                                     │
│  ⚠️  Brand Search Alert: $3,200 spent on "Nike"   │
│     brand keywords — 78% of these buyers already    │
│     visited nike.com directly. ROI: unclear.       │
│                                                     │
│  [View Full Report]  [Export PDF]                  │
└─────────────────────────────────────────────────────┘
```

#### Weekly Review: Cross-Platform View (Web App)

Every Sunday, the marketer opens the Web App to see the full week:

```
┌──────────────────────────────────────────────────────┐
│  Weekly Attribution Summary — Jun 10–16              │
├──────────────────────────────────────────────────────┤
│  Platform     Reported ROAS    True ROAS    Inflation│
│  ─────────    ─────────────   ─────────    ─────────│
│  Meta Ads         4.2x           2.1x        -50%   │
│  Google Ads       3.8x           1.9x        -50%   │
│  Combined         7.2x           3.1x        -57%   │
│                                                      │
│  Total Spend: $47,200                              │
│  Over-counted Conversions: 891 (44% of total)       │
│  Wasted Brand Search Spend: $8,100                  │
│                                                      │
│  📊 Week-over-week: ROAS dropped from 3.4x → 3.1x  │
│     (retargeting campaigns inflating Meta ROAS)     │
└──────────────────────────────────────────────────────┘
```

---

### Extension vs. Web App: What's the Difference?

| Dimension | Chrome Extension | Web App |
|-----------|----------------|---------|
| **Setup** | 2 minutes, API key paste | 5 minutes, account creation |
| **Data input** | Automatic (reads page) | Manual CSV upload or API |
| **Analysis scope** | Single platform per tab | Cross-platform aggregate |
| **Historical depth** | Last 30 days | Last 12 months |
| **Persistence** | Session only | Full history, comparisons |
| **Multi-store** | ❌ | ✅ Pro/Agency tiers |
| **Team collaboration** | ❌ | ✅ |
| **Report export** | PDF (basic) | PDF + HTML (detailed) |
| **Scheduled reports** | ❌ | ✅ Email/digest |
| **Alerts** | On-page overlay only | Email + Slack |
| **Target user** | Daily check, quick insight | Deep dive, weekly review |
| **Upsell path** | → Web App for full features | Extension already funneling |
| **Can be self-hosted** | ❌ (browser extension, always calls home) | ✅ (OSS license) |

### The Key Insight: Extension Cannot Be Self-Hosted

This is the strategic difference. The Streamlit Web App is MIT-licensed open source — once cloned, a merchant has everything and never pays.

The Chrome Extension is a **hosted service with a thin client**. The audit engine logic, Shopify API calls, and data aggregation all run against our backend. Self-hosting the extension is not possible. This is the lock-in mechanism that makes the extension viable as a business.

---

### Extension Monetization

| Tier | Price | Features |
|------|-------|----------|
| **Free** | $0 | 1 store, 7-day history, single platform per session, basic scorecard |
| **Pro** | $9.99/mo | Unlimited history, cross-platform view, brand cannibalization alerts, PDF reports, multi-tab comparison |
| **Agency** | $49/mo per client | All Pro features, client management, white-label reports, API access |

**Pricing rationale:** $9.99/mo is low enough that any merchant spending $5K+/month on ads won't hesitate. It's the cost of one cup of coffee per day. The upgrade to Pro should feel like a no-brainer after the free tier shows its value.

---

## 4. Target Market & Users

### Beachhead

Shopify D2C brands with:
- **Ad spend:** $10K–$500K/month on Meta + Google Ads
- **Team size:** 2–10 person marketing teams
- **Geography:** US/CA/UK/AU (English-speaking, Shopify-native)
- **Revenue:** $1M–$50M ARR

### User Personas

1. **Performance Marketer** — Runs the paid ads, owns the ROAS numbers. Opens Meta/Google dashboards every morning. Pain: "My dashboard shows 4x but I can't verify it."

2. **Founder/Owner** — Reviews ad performance weekly, makes budget decisions. Pain: "I trust my marketer but I want independent numbers."

3. **Agency Account Manager** — Manages 5–10 client accounts, needs fast verification. Pain: "Client thinks I'm overselling — I need proof that backs my recommendations."

---

## 5. Competitive Landscape

| Competitor | Type | Pricing | Chrome Extension | Shopify-Native | Independence |
|---|---|---|---|---|---|
| **Rockerbox** | MTA + MMM | Enterprise ($100K+/yr) | ❌ | Partial | Partial |
| **Triple Whale** | E-com attribution | $500–$5K/mo | ❌ | ✅ Yes | ✅ |
| **Northbeam** | MTA / dark funnel | Mid-market | ❌ | Partial | ✅ |
| **Littledata** | Server-side tracking | $99–$999/mo | ❌ | ✅ Yes | ✅ |
| **Hyros** | AI attribution | $2K+/mo | ❌ | Yes | ✅ |
| **DIY Spreadsheets** | Manual | $0 | ❌ | No | ✅ |
| **Google Ads Reports** | Platform-native | Free | ✅ (sort of) | ❌ | ❌ |
| **Ad Audit Extension** | Independent extension | $9.99/mo | ✅ | ✅ Yes | ✅ |

### Our Differentiation

1. **Only Chrome extension with real-time Shopify-verified ROAS** — Triple Whale and Northbeam are web apps only. No one else does in-dashboard verification.

2. **Shopify ground truth, not pixel-based** — Littledata and Hyros rely on server-side tracking pixels. We use Shopify's order database as the source of record.

3. **Independent, not VC-backed** — Triple Whale ($25M), Rockerbox ($40M+), Northbeam ($15M) all have investor pressure to grow. We don't.

4. **$9.99/mo vs $500+/mo** — We're 50x cheaper than the nearest competitor with comparable methodology.

---

## 6. MoSCoW Feature Prioritization

### Must Have — Chrome Extension MVP (Weeks 1–4)

- [ ] Chrome Extension scaffold (manifest v3)
- [ ] Shopify API connector (OAuth, read-only)
- [ ] Meta Ads page detection + data extraction
- [ ] Google Ads page detection + data extraction
- [ ] Basic audit engine (de-duplication, incremental ROAS)
- [ ] Attribution Accuracy Score overlay UI
- [ ] Free tier (7-day history, single platform)
- [ ] Chrome Web Store listing

### Must Have — Web App MVP (Weeks 1–4, parallel)

- [ ] Streamlit app with basic CSV upload
- [ ] Full audit engine (de-dup, cannibalization, ROAS)
- [ ] PDF report export
- [ ] Basic auth (email/password)
- [ ] SQLite audit history
- [ ] Stripe integration

### Should Have — Extension Pro (Weeks 5–8)

- [ ] Cross-platform comparison view
- [ ] Brand search cannibalization alerts
- [ ] 30-day historical analysis
- [ ] PDF report export from extension
- [ ] Multi-tab comparison
- [ ] Pro tier billing ($9.99/mo)

### Should Have — Web App v1.0 (Weeks 5–10)

- [ ] AI-powered summaries (OpenAI)
- [ ] Health check alerts (email)
- [ ] Trend charts (7/30/90 day)
- [ ] Onboarding wizard
- [ ] Full SQLite persistence

### Could Have — v2.0

- [ ] Google Search Console integration (brand cannibalization)
- [ ] TikTok Ads support
- [ ] Agency dashboard (multi-tenant)
- [ ] Industry benchmarking (anonymized aggregates)
- [ ] White-label for agencies

---

## 7. Open Questions (Resolved)

### ❌ OLD: "Open-source will kill paid adoption"

**Resolved:** The Chrome Extension cannot be self-hosted. Open-source the Web App as credibility + SEO, not as the product. The extension creates the actual revenue.

### ❌ OLD: "How do merchants share awkward audit results?"

**Resolved:** The Chrome Extension shows results in-dashboard, privately. No need to share externally. The sharing mechanism is: "I use this extension" → peer curiosity → installs. Viral loop is built into the daily workflow.

### ❓ NEW: "What if Shopify changes their API and breaks the extension?"

**Mitigation:** Build API version pinning, error messaging that guides users to re-authenticate, and a monitoring alert when API error rates spike. The Shopify API is stable; breaks are rare and usually recoverable.

### ❓ NEW: "How does the extension detect which conversions are real?"

**The methodology (simplified for UI):**
1. Pull all Shopify orders in date range
2. Pull all Meta/Google reported conversions in same range
3. Match via: time window (7-day click window) + amount (order total within 10% of reported AOV)
4. Count matched vs. unmatched
5. Unmatched but reported = likely inflated
6. Matched across both platforms = de-duplicated

**The display is simple. The methodology is defensible. We'll publish a white paper.**

---

## 8. Monetization Strategy

### Primary Model: Chrome Extension SaaS

| Tier | Price | Features | Target |
|------|-------|----------|--------|
| Free | $0 | 1 store, 7-day history, single platform, basic scorecard | Trialists |
| Pro | $9.99/mo | Unlimited history, cross-platform, brand alerts, PDF export | Individual merchants |
| Agency | $49/mo/client | Pro features, client management, white-label, API | Shopify agencies |

### Secondary Model: Web App SaaS

| Tier | Price | Features | Target |
|------|-------|----------|--------|
| Starter | $49/mo | 1 store, 30-day data, CSV only | Micro-SMB |
| Growth | $149/mo | 1 store, 90-day data, API connectors, alerts | SMB ($5K–$50K/mo ad spend) |
| Pro | $299/mo | 3 stores, 12-month data, team access | Mid-market |

### Revenue Targets (Revised)

| Year | Extension Users | Ext ARR | Web App Customers | Web ARR | Total ARR |
|------|----------------|---------|------------------|---------|----------|
| 1 | 5,000 | $300K | 200 | $360K | $660K |
| 2 | 20,000 | $1.8M | 800 | $1.4M | $3.2M |
| 3 | 80,000 | $7.2M | 2,500 | $4.5M | $11.7M |

### Unit Economics

- **Extension CAC:** $0–5 (organic from Chrome Web Store + HN/PH launch)
- **Web App CAC:** $50–150 (extension funnel + content)
- **Extension LTV:** $9.99 × 18 months avg = $180
- **Web App LTV:** $200 × 24 months = $4,800
- **LTV:CAC (extension):** >30:1
- **LTV:CAC (web app):** >20:1

---

## 9. Roadmap

### Phase 1: Extension MVP (Weeks 1–4)

**Goal:** Ship Chrome Extension to Chrome Web Store, get first 100 installs

- [ ] Extension scaffold (manifest v3)
- [ ] Shopify API connector
- [ ] Meta Ads data extraction
- [ ] Google Ads data extraction
- [ ] Audit engine (de-dup + ROAS)
- [ ] Scorecard overlay UI
- [ ] Free tier + Stripe
- [ ] Chrome Web Store submission
- [ ] Hacker News launch

### Phase 2: Web App + Extension Pro (Weeks 5–10)

**Goal:** Build the funnel, convert free → paid

- [ ] Streamlit Web App (full CSV + API ingestion)
- [ ] Cross-platform comparison view
- [ ] Brand cannibalization alerts
- [ ] AI summaries
- [ ] Agency tier
- [ ] First 1,000 installs

### Phase 3: Growth (Months 4–12)

**Goal:** 5,000 extension users, 200 paying Web App customers

- [ ] TikTok Ads support
- [ ] Google Search Console integration
- [ ] Agency partner program
- [ ] Content marketing (audit methodology blog posts)
- [ ] Shopify App Store listing

### Phase 4: Scale (Year 2)

**Goal:** 20,000+ extension users, industry benchmark data moat

- [ ] Anonymized industry benchmark reports
- [ ] Sell benchmark data to ad platforms/agencies
- [ ] White-label for Shopify app developers

---

## 10. Success Metrics

### North Star

**Chrome Extension Installs → Pro Conversion Rate**

Target: 5% of free users upgrade to Pro within 30 days

### Secondary Metrics

| Metric | Target (12 months) |
|--------|-------------------|
| Extension installs | 10,000 |
| Extension Pro paying | 500 |
| Web App paying | 200 |
| Combined MRR | $25K |
| Churn (Pro) | <3%/month |
| NPS | ≥50 |

---

## Appendix: Technical Notes

### How Extension Reads Data

The extension uses **Content Scripts** (injected JavaScript) that run on Meta Ads Manager and Google Ads pages. These scripts:
1. Read the DOM table data (campaign, spend, conversions, ROAS)
2. Extract date range from page context
3. Send data to the extension's background service worker
4. Background worker calls Shopify API for order data
5. Audit engine runs in browser (WASM-compiled Python or pure JS)
6. Results cached locally in chrome.storage.local

**No data is sent to our servers without user consent.** All audit computation is local. The only external calls are:
- Shopify API (user's own store, authenticated by user's API key)
- (Future) Our backend for cross-platform aggregation + benchmark data

### Security Model

- Shopify API keys are stored in Chrome's encrypted storage (`chrome.storage.session`), not in plain text or localStorage
- No data leaves the browser except to Shopify's API
- Cross-platform aggregation (Phase 2) requires opt-in and anonymization
- We never see individual merchant's revenue or ROAS data

---

*PRD version 1.1 — 2026-04-15: Chrome Extension Strategy Added*
