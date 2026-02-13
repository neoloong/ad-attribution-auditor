# Ad Attribution Auditor — Project State

## Last Updated: 2026-02-09

---

## What This Project Is

An independent ad attribution auditor that cross-references ad platform claims (Meta Ads, Google Ads) against actual e-commerce orders (Shopify) to calculate **true incremental ROAS**. It detects:
- **De-duplication**: How much platforms over-count conversions
- **Cannibalization**: When platforms claim credit for users already searching your brand
- **True Incremental ROAS**: Real return after removing inflated claims

Built as a Streamlit web app with a modular Python backend.

---

## Architecture

```
ad_tech/
├── app.py                          # Streamlit entry point
├── pages/
│   ├── 1_Upload_Data.py            # CSV upload + validation UI (6 data sources)
│   ├── 2_Run_Audit.py              # Audit configuration + execution UI
│   ├── 3_Dashboard.py              # Health checks, charts, trends, period comparison, search terms
│   ├── 4_Report.py                 # AI summary + HTML export
│   └── 5_API_Connections.py        # Shopify/Meta/Google Ads API credential management
├── ad_audit/
│   ├── ingestion/
│   │   ├── schemas.py              # Column schemas for each CSV type
│   │   ├── loader.py               # CSV loading (path or file-like)
│   │   ├── validators.py           # Schema validation
│   │   └── normalizer.py           # Column rename, type coercion, UTM/click-ID extraction
│   ├── engine/
│   │   ├── models.py               # Dataclasses: AuditConfig, AuditResult, DeduplicationResult, etc.
│   │   ├── aggregate_audit.py      # Time-series audit: daily merge → correlation → dedup → cannibalization → iROAS
│   │   ├── deduplication.py        # Platform-reported vs actual conversion comparison
│   │   ├── cannibalization.py      # Brand-search overlap scoring
│   │   ├── incremental_roas.py     # Reported vs true incremental ROAS
│   │   ├── user_level_audit.py     # Email-hash / click-ID matching with time-window joins
│   │   ├── health_checks.py        # Configurable threshold-based alerts (CRITICAL/WARNING/INFO)
│   │   ├── period_comparison.py    # Period-over-period comparison with root cause attribution
│   │   └── search_term_analysis.py # Search term wasted spend analysis with Shopify cross-reference
│   ├── visualization/
│   │   ├── charts.py               # Plotly chart builders
│   │   ├── dashboard.py            # Dashboard layout helpers
│   │   └── trend_charts.py         # Rolling-window trend charts (duplication, ROAS, cannibalization)
│   ├── connectors/
│   │   ├── base.py                 # BaseConnector ABC (test_connection, fetch_data)
│   │   ├── shopify_api.py          # Shopify REST Admin API connector
│   │   ├── meta_api.py             # Meta Marketing API connector
│   │   └── google_ads_api.py       # Google Ads API (GAQL) connector + search terms
│   ├── report/
│   │   ├── llm_summary.py          # OpenAI-powered narrative summary
│   │   ├── html_export.py          # Standalone HTML report with embedded Plotly
│   │   └── templates/
│   │       └── report_base.html    # Jinja2 HTML template
│   └── utils/
│       ├── config.py               # LLM model config, constants
│       ├── date_utils.py           # Date parsing helpers
│       └── hash_utils.py           # Email hashing
├── scripts/
│   └── generate_mock_data.py       # Generates 6 sample CSVs
├── data/                           # Generated sample CSVs
│   ├── sample_meta_ads.csv
│   ├── sample_google_ads.csv
│   ├── sample_shopify_orders.csv
│   ├── sample_gsc_brand_search.csv
│   ├── sample_search_terms.csv
│   └── sample_user_matched.csv
├── tests/
│   ├── conftest.py                 # Shared fixtures (all 5 data types)
│   ├── test_ingestion/             # loader, validators, normalizer tests
│   ├── test_engine/                # aggregate_audit, deduplication, cannibalization, iROAS, user-level tests
│   └── test_integration/           # End-to-end: CSV → audit → report
└── docs/
    ├── competitive_analysis_adalysis.md
    └── project_state.md            # This file
```

---

## Data Model (After Multi-Platform Support)

### Supported Data Sources

| Source | Required? | Schema Name | Key Columns After Normalization |
|---|---|---|---|
| Meta Ads CSV | At least one ad platform | `meta_ads` | date, campaign_name, spend, reported_conversions, reported_revenue, reported_roas, **platform="meta"** |
| Google Ads CSV | At least one ad platform | `google_ads` | date, campaign_name, spend, reported_conversions, reported_revenue, reported_roas, **platform="google_ads"** |
| Shopify Orders CSV | Always required | `shopify_orders` | order_id, email, date, revenue, referring_site, landing_site, utm_source, utm_medium, utm_campaign, fbclid, **gclid**, email_hash |
| GSC Brand Search CSV | Optional | `gsc_brand_search` | date, query, clicks, impressions |
| Search Terms CSV | Optional | `search_terms` | search_term, campaign_name, spend, reported_conversions, impressions, clicks, reported_revenue, ad_group, search_term_lower |
| User-Matched Events CSV | Optional (enables user-level mode) | `user_matched` | user_id, email_hash, event_type, event_source, timestamp, revenue, fbclid, **gclid** |

### Key Design Decisions
- Ad platform DataFrames are **pre-concatenated** before passing to the engine (`pd.concat([meta_df, google_ads_df])`)
- The `platform` column identifies the source but the engine treats all ad data uniformly
- `gsc_df` can be `None` — cannibalization scoring is simply skipped
- User-level audit accepts both `"ad_click"` (new) and `"meta_click"` (legacy) event types
- Click matching supports both `fbclid` (Meta) and `gclid` (Google Ads)

---

## Engine Pipeline

### Aggregate Audit (`run_aggregate_audit(ad_df, shopify_df, gsc_df=None, config=None)`)
1. `_build_daily_merged()` — group ad + shopify + optional GSC by date, outer merge
2. Classify spend-on/off days (threshold from config)
3. `_organic_baseline()` — avg daily Shopify conversions during spend-off periods
4. `_incremental_per_day()` — spend-on avg minus organic baseline
5. `_rolling_correlation()` — rolling Pearson r between spend and actual conversions
6. `compute_deduplication()` — compare platform-reported vs actual conversions
7. `compute_cannibalization()` — brand-search overlap scoring (skipped if no GSC)
8. `compute_incremental_roas()` — reported vs true incremental ROAS

### User-Level Audit (`run_user_level_audit(user_events_df, config=None)`)
1. Split events: ad clicks (meta_click or ad_click), purchases, brand searches
2. `_match_purchases_to_clicks()` — email_hash + time window, then fbclid/gclid fallback
3. `_check_brand_search_overlap()` — flag cannibalized orders
4. Compute truly incremental vs cannibalized counts

### Key Model Fields
- `DeduplicationResult`: `platform_reported_conversions`, `actual_conversions`, `overlap_count`, `duplication_rate`
- `CannibalizationResult`: `cannibalized_days`, `total_days`, `cannibalization_score`, `cannibalized_revenue_fraction`
- `IncrementalROASResult`: `reported_roas`, `true_incremental_roas`, `inflation_rate`, `total_spend`, `reported_revenue`, `incremental_revenue`

---

## Test Status

- **70 tests pass** (pytest)
- **65% overall code coverage** (pytest --cov=ad_audit)
  - Core engine modules: 89-100% coverage
  - API connectors: 0% (require real credentials to test)
  - LLM summary: 0% (requires OpenAI API key)
  - Trend charts/dashboard: 0% (visualization helpers)
- Test structure: unit tests per module + integration end-to-end tests
- Key test classes: `TestMultiPlatformEndToEnd`, `TestGracefulDegradation`, `TestEdgeCases`

---

## Change Log

### Session 3 (2026-02-09): Competitive Features

All 5 high-priority features from competitive analysis implemented:

1. **Health Check Alerts** (`ad_audit/engine/health_checks.py`)
   - `Severity` enum: CRITICAL, WARNING, INFO
   - `HealthCheckThresholds` with configurable defaults (duplication, inflation, cannibalization, correlation)
   - `run_health_checks(result, thresholds)` → sorted list of `HealthCheckAlert`
   - 8 tests covering all severity levels, custom thresholds, sorting

2. **Trend Dashboards** (`ad_audit/visualization/trend_charts.py`)
   - `rolling_duplication_rate_chart()` — rolling duplication rate with fill
   - `rolling_roas_comparison_chart()` — reported vs actual ROAS with inflation gap shading
   - `cannibalization_trend_chart()` — rolling cannibalization score
   - `organic_vs_incremental_trend()` — stacked area: organic baseline vs actual

3. **Period-over-Period Comparison** (`ad_audit/engine/period_comparison.py`)
   - `compare_periods(ad_df, shopify_df, split_date, gsc_df)` — splits data, runs 2 audits, computes deltas
   - `MetricDelta` with direction property (increased/decreased/unchanged)
   - `_attribute_root_causes()` — plain-English explanations
   - 4 tests covering basic, root causes, GSC inclusion, delta direction

4. **Search Term Wasted Spend Analysis** (`ad_audit/engine/search_term_analysis.py`)
   - `analyze_search_terms(search_terms_df, shopify_df, brand_terms)` — cross-references with Shopify-verified orders
   - `SearchTermInsight` per-term, `SearchTermAnalysisResult` with aggregates
   - Proportional allocation heuristic for order-to-term matching
   - 5 tests covering basic, brand detection, empty inputs, sorting
   - New schema: `search_terms` in schemas.py + `normalize_search_terms()`

5. **API Connector Layer** (`ad_audit/connectors/`)
   - `BaseConnector` ABC with `test_connection()`, `fetch_data()`, `source_name`
   - `ShopifyConnector` — REST Admin API with pagination
   - `MetaAdsConnector` — Marketing API insights endpoint
   - `GoogleAdsConnector` — GAQL with `fetch_data()` + `fetch_search_terms()`
   - Streamlit page `5_API_Connections.py` for credential management

6. **Dashboard Overhaul** (`pages/3_Dashboard.py`)
   - Health check alerts section at top (color-coded by severity)
   - Trends Over Time section with configurable rolling window slider
   - Period-over-Period Comparison with date splitter + root cause analysis
   - Search Term Wasted Spend section with KPIs and table

### Session 2 (2026-02-09): Multi-Platform Support

1. **Ingestion**: Added Google Ads schema + `normalize_google_ads()` + `platform` column on all ad data + `gclid` extraction from URLs
2. **Engine**: Renamed `meta_reported_conversions` → `platform_reported_conversions`, `shopify_actual_conversions` → `actual_conversions`; `run_aggregate_audit()` now takes `ad_df` (pre-concatenated) + optional `gsc_df=None`; user-level audit supports `ad_click` event type + `gclid` matching
3. **Visualization**: Labels changed from "Meta"/"Shopify" to "Ad Platform"/"Actual"
4. **Streamlit**: Multi-platform upload page, concat logic in Run Audit, updated sidebar
5. **Mock data**: New `sample_google_ads.csv` + updated user-matched data with `ad_click` + `gclid`
6. **Tests**: Multi-platform, graceful degradation, gclid matching

### What's NOT Done Yet
See `docs/competitive_analysis_adalysis.md` for full roadmap. Remaining priorities:
- Budget reallocation recommendations based on true incremental ROAS
- Free Attribution Truth Score (lead gen funnel)
- Real API credential testing (connectors built but need live accounts)
- Scheduled / always-on monitoring (cron / background jobs)
- Multi-channel attribution modeling (beyond last-click)

---

## Running the Project

```bash
# Generate sample data
.venv/bin/python scripts/generate_mock_data.py

# Run tests
.venv/bin/python -m pytest tests/ -v

# Run with coverage
.venv/bin/python -m pytest tests/ --cov=ad_audit

# Start Streamlit app
.venv/bin/streamlit run app.py
```

---

## Tech Stack
- Python 3.9+
- Streamlit (web UI)
- Pandas (data processing)
- Plotly (charts)
- Scipy (correlation analysis)
- Jinja2 (HTML reports)
- OpenAI SDK (LLM summaries)
- pytest + pytest-cov (testing)
