# PRD: Ad Attribution Auditor

**Project:** https://github.com/neoloong/ad-attribution-auditor
**Date:** 2026-04-14
**Author:** PM Agent

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

## 2. Target Market & Users

### Beachhead

Shopify D2C brands with:
- **Ad spend:** $10K–$500K/month on Meta + Google Ads
- **Team size:** 2–10 person marketing teams
- **Geography:** US/CA/UK/AU (English-speaking, Shopify-native)
- **Revenue:** $1M–$50M ARR

### User Personas

1. **Performance Marketer** — Runs the paid ads, owns the ROAS numbers, needs to justify spend to founder or report to agency. Pain: "My Meta dashboard shows 4x but revenue doesn't match."

2. **Founder/Owner** — Makes budget decisions, trusts the numbers but has a nagging suspicion. Pain: "We're spending $50K/month and I can't tell if it's working."

3. **Agency Account Manager** — Manages multiple client accounts, needs fast independent verification. Pain: "Client thinks I'm overselling — I need proof."

### Market Sizing

- ~4.6M Shopify merchants globally, ~1.75M paying
- ~500K actively running Meta + Google Ads
- ~50K–100K in the sweet spot ($10K–$500K/month ad spend)
- SAM: $1–3B | SOM: $50M–$200M ARR (3-year, focused)

---

## 3. Competitive Landscape

| Competitor | Type | Pricing | Shopify-Native | Positioning |
|---|---|---|---|---|
| **Rockerbox** | MTA + MMM | Enterprise ($100K+/yr) | Partial | Full-suite, enterprise |
| **Triple Whale** | E-com attribution | Mid-market ($500–$5K/mo) | ✅ Yes | Shopify-first, incrementality |
| **Northbeam** | MTA / dark funnel | Mid-market | Partial | Cross-device, full-funnel |
| **Measured** | MMM / Incrementality | Enterprise | No | Causal incrementality testing |
| **Littledata** | Server-side tracking | $99–$999/mo | ✅ Yes | Shopify + Headless |
| **Hyros** | AI attribution | High ($2K+/mo) | Yes | AI-powered, replaces GA |
| **DIY Spreadsheets** | Manual | $0 | No | Time-intensive, error-prone |

### Our Differentiation

- **Independence**: Not a platform, not VC-backed with growth mandates — the merchant's advocate
- **Accessibility**: SMB-friendly pricing vs. enterprise-only incumbents
- **Open-source**: Self-host or SaaS, no lock-in
- **Shopify-native**: Built for Shopify merchants, not adapted from enterprise

---

## 4. MoSCoW Feature Prioritization

### Must Have (MVP)

- [ ] CSV ingestion for Meta Ads + Google Ads + Shopify Orders
- [ ] Aggregate audit mode: de-duplication across channels
- [ ] True incremental ROAS calculation (vs. reported ROAS)
- [ ] Cannibalization detection (brand-search overlap)
- [ ] Basic dashboard with key metrics
- [ ] Period comparison (before/after)
- [ ] PDF/HTML report export

### Should Have (v1.0)

- [ ] Wasted spend analysis (high-spend keywords, zero verified purchases)
- [ ] Health check alerts (configurable thresholds)
- [ ] User-level audit mode (email hash matching)
- [ ] Trend analysis (rolling 7/30/90 day metrics)
- [ ] AI-powered plain-English summaries (OpenAI)
- [ ] Onboarding wizard
- [ ] Email report scheduling

### Could Have (v2.0)

- [ ] Live API connectors (Shopify, Meta, Google Ads — auto-pull)
- [ ] TikTok Ads support
- [ ] Campaign drill-down
- [ ] Anomaly detection (AI-powered)
- [ ] Industry benchmarking (anonymized)
- [ ] CLV overlay
- [ ] Agency multi-account dashboard
- [ ] White-label for agencies

---

## 5. Monetization Strategy

### Pricing Tiers

| Tier | Price | Features | Target |
|------|-------|----------|--------|
| **Free / OSS** | $0 | Self-host, full features, manual CSV | Developers, micro-merchants |
| **Starter** | $99/mo | 1 store, 30-day data, 5 reports/mo, email support | <$5K/mo ad spend |
| **Growth** | $249/mo | 1 store, 90-day data, unlimited reports, API connectors, alerts | $5K–$50K/mo ad spend |
| **Pro** | $499/mo | 3 stores, 12-month data, team access, custom dashboards | $50K–$200K/mo ad spend |
| **Agency** | $599/mo per client | Multi-client, branded reports, API access, priority support | Shopify agencies |
| **Enterprise** | Custom | Unlimited, dedicated infra, SLA, custom integrations | >$200K/mo ad spend |

**Annual discount:** 2 months free (17% off) for annual commitment.

### Revenue Targets

| Year | Paying Customers | Avg/Mo | ARR |
|------|-----------------|--------|-----|
| 1 | 200 | $300 | $720K |
| 2 | 800 | $350 | $3.36M |
| 3 | 2,500 | $400 | $12M |

### Unit Economics

- **LTV:CAC target:** >3:1
- **Payback period:** <6 months
- **Churn target:** <5%/month
- **Gross margin:** 80–90%

---

## 6. Roadmap

### MVP — Weeks 1–8

**Goal:** Validate core audit logic, no UI yet, proof-of-concept

- [ ] CSV ingestion (Meta, Google, Shopify)
- [ ] Aggregate audit engine (de-dup, cannibalization, incremental ROAS)
- [ ] Internal testing with sample data
- [ ] Validate organic baseline methodology (rebuild if needed)
- [ ] **Decision gate:** Does the math hold? Do real merchants see meaningful inflation?

### v1.0 — Weeks 9–20

**Goal:** Ship a usable SaaS product

- [ ] 5-page Streamlit UI (Dashboard, Upload, Audit Results, Reports, Settings)
- [ ] PDF export
- [ ] AI-powered summaries (OpenAI)
- [ ] Health check alerts
- [ ] SQLite persistence (audit history)
- [ ] Basic auth (email/password)
- [ ] Onboarding wizard
- [ ] Stripe integration (payments)
- [ ] Deploy to cloud (Railway/Render)

### v2.0 — Weeks 21–36

**Goal:** Scale, automate, expand

- [ ] Live API connectors (Shopify, Meta, Google Ads)
- [ ] TikTok Ads support
- [ ] Agency dashboard (multi-tenant)
- [ ] White-label for agencies
- [ ] Anomaly detection
- [ ] Industry benchmarking
- [ ] Mobile app (stretch)

---

## 7. Success Metrics

### North Star

**True Incremental ROAS Delta** = Reported ROAS − Audited ROAS

This is the core value proposition. If merchants consistently find large deltas, the tool is validated. If deltas are small, the product needs repositioning.

### Secondary Metrics

| Metric | Target (12 months) |
|--------|-------------------|
| MRR | $15K |
| Paid subscribers | 75 |
| Churn | <5%/month |
| NPS | ≥40 |
| LTV:CAC | >3:1 |
| GitHub stars | 1,000+ |

### Leading Indicators

- Audit upload completion rate
- PDF report download rate
- Free → Paid conversion rate
- Time-to-first-audit
- Repeat audit rate

---

## 8. Open Questions

1. **Distribution strategy**: Early audits showing devastating inflation are validating but awkward — merchants don't share results that make them look bad. How do we get testimonials? Perhaps: audits showing *surprising efficiency* (more incremental than expected) are more shareable.

2. **Organic baseline methodology**: The current `spend=0 days` approach is methodologically weak. Better approaches (holdout, geo-based incrementality tests, Bayesian structural time-series) are more defensible but add complexity.

3. **Email hash matching ceiling**: Cross-platform identity is inherently approximate. What's the realistic accuracy ceiling, and how do we set user expectations?

4. **Platform anti-scraping**: Meta/Google may restrict CSV access or change schema frequently enough to create maintenance burden. Build schema versioning and monitoring.

---

*PRD version 1.0 — 2026-04-14*
