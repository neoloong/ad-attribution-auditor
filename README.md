# Ad Attribution Auditor

<p align="center">
  <strong>Don't let Big Tech grade their own homework.</strong><br>
  An independent, open-source tool that audits ad platform attribution claims.
</p>

<p align="center">
  <a href="https://ad-attribution-auditor-next.vercel.app"><img src="https://img.shields.io/badge/live-demo-green" alt="Live demo"></a>
  <a href="https://github.com/neoloong/ad-attribution-auditor/blob/main/LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="License: MIT"></a>
  <img src="https://img.shields.io/badge/python-3.9+-blue" alt="Python 3.9+">
  <img src="https://img.shields.io/badge/next.js-16-000000?logo=nextdotjs" alt="Next.js">
</p>

<p align="center">
  <strong><a href="https://ad-attribution-auditor.vercel.app">Landing page</a></strong> ·
  <strong><a href="https://www.upwork.com/services/product/marketing-incremental-roas-audit-of-meta-google-ads-estimated-from-shopify-orders-2124818567336541716">Order the audit on Upwork</a></strong><br>
  One-off incremental ROAS audit of your Meta &amp; Google ads, estimated from your Shopify orders — interactive report + PDF.
</p>

---

## Two Flavors

This repo contains **two implementations** of the same engine:

| | Python (Streamlit) | Next.js (React) |
|---|---|---|
| **Directory** | `ad_audit/` + `pages/` | `web/` |
| **Run** | `streamlit run app.py` | `cd web && npm run dev` |
| **Strengths** | 70 tests, user-level audit, API connectors | Modern UI, Recharts dashboards, browser-side processing |
| **Best for** | Data scientists, batch processing, API integration | DTC brands, live demo, client-side privacy |

**[Live demo →](https://ad-attribution-auditor-next.vercel.app/dashboard?demo=true)**

---

An independent tool that audits ad platform attribution claims by cross-referencing **Meta Ads** and **Google Ads** reports against actual **Shopify** orders to calculate **true incremental ROAS**.

## The Problem

Ad platforms self-report conversions, and they have every incentive to inflate the numbers. A user who was already going to buy gets counted as a "conversion" by every platform that touched them. Your reported 4x ROAS might really be 1.5x.

## What This Tool Does

- **De-duplication** — Identifies conversions over-counted across channels
- **Cannibalization Detection** — Finds users who would have purchased anyway (already brand-searching)
- **True Incremental ROAS** — Real return after removing inflated claims
- **Health Check Alerts** — Automated warnings when metrics cross configurable thresholds
- **Trend Analysis** — Rolling metrics over time (duplication rate, ROAS, cannibalization)
- **Period Comparison** — Split by date to see what changed and why
- **Search Term Wasted Spend** — High-spend keywords with zero verified purchases
- **AI-Powered Reports** — LLM-generated plain-English summaries

## Architecture

```
ad_audit/
├── ingestion/       # CSV loading, schema validation, normalization
├── engine/          # Audit algorithms (aggregate + user-level)
├── visualization/   # Plotly charts and trend dashboards
├── connectors/      # Shopify, Meta, Google Ads API integrations
├── report/          # LLM summaries + HTML export
└── utils/           # Config, date parsing, hashing

pages/               # Streamlit multi-page UI (5 pages)
tests/               # 70 tests across unit, engine, and integration
data/                # Sample CSVs for demo
```

## Quick Start

### Python (Streamlit)
```bash
git clone https://github.com/neoloong/ad-attribution-auditor.git
cd ad-attribution-auditor
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

### Next.js (Web App)
```bash
git clone https://github.com/neoloong/ad-attribution-auditor.git
cd ad-attribution-auditor/web
npm install
npm run dev
```
Then open http://localhost:3000/dashboard?demo=true for the demo.

Sample data is included in `data/` — upload the CSV files to try it immediately.

## Audit Modes

### Aggregate Audit
Time-series analysis: groups daily ad spend and Shopify orders, calculates organic baseline from zero-spend days, and measures true incremental conversions via Pearson correlation.

**Inputs:** Meta Ads CSV + Google Ads CSV + Shopify Orders CSV + optional GSC Brand Search CSV

### User-Level Audit
Individual order attribution: matches purchases to ad clicks via email hash and `fbclid`/`gclid` click IDs within a configurable time window, then checks brand-search overlap.

**Inputs:** User-Matched Events CSV (clicks, purchases, brand searches)

## Data Sources

| Source | Required | Purpose |
|--------|----------|---------|
| Meta Ads CSV | At least one ad platform | Ad spend and reported conversions |
| Google Ads CSV | At least one ad platform | Ad spend and reported conversions |
| Shopify Orders CSV | Always | Ground truth: actual orders and revenue |
| GSC Brand Search CSV | Optional | Detects cannibalization of organic intent |
| Search Terms CSV | Optional | Wasted spend analysis |
| User-Matched Events CSV | Optional | Enables user-level audit mode |

## Running Tests

```bash
# All tests
python -m pytest tests/ -v

# With coverage
python -m pytest tests/ --cov=ad_audit
```

70 tests passing, 65% overall coverage (89-100% on core engine modules).

## Tech Stack

| Component | Python | Next.js |
|---|---|---|
| Language | Python 3.9+ | TypeScript |
| UI | Streamlit | React 19 + shadcn/ui + Tailwind CSS v4 |
| Charts | Plotly | Recharts |
| Data | Pandas + SciPy | PapaParse + native TS |
| AI | OpenAI SDK | (planned) |
| Tests | pytest (70 tests) | eslint + tsc |

## License

MIT
