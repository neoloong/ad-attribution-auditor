# Technical Assessment Report: Ad Attribution Auditor

**Repo:** https://github.com/neoloong/ad-attribution-auditor
**Date:** 2026-04-14
**Analyst:** SDET Agent (Software Development & Engineering)
**Test Results:** 70 tests pass, 65% overall code coverage

---

## 1. Architecture Review

**Verdict: Sound at the component level, but not designed for scale or production multi-tenancy.**

### Component Quality

| Layer | Contents | Quality |
|-------|----------|---------|
| `ingestion/` | CSV loading, normalization, schema validation | ✅ Well-structured |
| `engine/` | Core audit algorithms | ✅ Good separation of concerns |
| `connectors/` | Shopify, Meta, Google Ads API clients | ✅ Decent abstraction (BaseConnector) |
| `visualization/` | Plotly chart builders | ✅ Stateless chart functions |
| `report/` | HTML export, LLM summarization | ✅ Template-based |
| `pages/` | 5 Streamlit pages | ✅ Reasonable page decomposition |

### Key Structural Issues

1. **All data lives in Streamlit `session_state`** — an in-memory Python dict. No persistence, no database, no cache. Every session rebuilds from scratch.

2. **No job queue or async processing** — API pulls and audits run synchronously in the Streamlit request thread. Large data = UI freeze.

3. **No data layer** — results are DataFrames and dataclasses, not stored. No audit history, no comparison across runs.

---

## 2. Implementation Challenges

### 2a. CSV Schema Changes (HIGH RISK)

Meta and Google Ads frequently rename columns. The schema definitions in `schemas.py` use hardcoded rename dictionaries:

```python
META_ADS_RENAME = {
    "Day": "date",
    "Campaign name": "campaign_name",
    ...
}
```

**Problem:** If Meta changes `"Campaign name"` → `"Campaign"`, the normalizer silently produces wrong/missing data. No schema versioning, no fuzzy-matching, no warning when known columns go missing.

**Mitigation needed:** Column alias mapping with fuzzy matching, schema version detection, breaking-change alerts.

### 2b. Email Hash Matching Accuracy (MEDIUM RISK)

SHA-256 email hashing is implemented correctly for privacy-safe matching, but:

- **Normalization is basic** — `.strip().lower()` handles common cases but not Gmail dot-account variants (`user@gmail.com` vs `u.ser@gmail.com`) or plus-suffix addresses
- **Matching is one-to-one** — if same person has different emails across Meta and Shopify (different devices, opted-out tracking), they'll never match
- **Attribution join is approximate** — when two clicks (one Meta, one Google) match same purchase, code picks *first* by time, which is arbitrary

```python
# user_level_audit.py — picks first click, not necessarily the right one
merged = merged.sort_values("time_diff").groupby("user_id").first().reset_index()
```

### 2c. Organic Baseline Calculation (HIGH RISK — Methodologically Questionable)

Organic baseline = average daily conversions on days when spend = 0:

```python
def _organic_baseline(daily):
    off = daily.loc[~daily["spend_on"], "actual_conversions"]
    return float(off.mean())
```

**Problems:**
- Days with $0 spend are NOT random — may be weekends, holidays, or post-campaign periods with systematically different buying behavior
- $0 spend doesn't mean $0 marketing — email, organic social, word-of-mouth may continue
- Small sample problem — most datasets have very few spend-off days, making the mean noisy
- Takes a *mean of means* across uneven time windows — biased result if spend-on days cluster unevenly

**Better methodologies exist:**
- Holdout experiments (control group with no ads)
- Geo-based incrementality tests (disable ads in select markets)
- Bayesian structural time-series models

### 2d. Time-Window Attribution Logic (MEDIUM RISK)

- 7-day window is static but products are variable — underweights high-consideration purchases
- Only handles clicks, not view-throughs (impression → purchase without click)
- Cross-device journeys handled via fbclid/gclid but not full identity graph

---

## 3. Scalability

**Verdict: Cannot handle 100s of concurrent users or large data volumes.**

| Issue | Impact |
|-------|--------|
| All data in Pandas DataFrames in memory | OOM risk on modest hardware with 1M+ rows |
| No incremental processing | Full reload every audit run |
| Single-threaded, synchronous | Single CPU, UI freeze on large data |
| Streamlit session_state | No true multi-user isolation without additional infra |

**What would work at scale:**
- Upload → cloud storage (S3) → processing job (Spark/Dask) → results in database
- Frontend polls for job completion, streams results
- This is essentially a rebuild of current architecture

---

## 4. Production Readiness

**Verdict: Not production-ready for multi-tenant SaaS. Single-user local use is fine.**

| Area | Missing |
|------|---------|
| **Auth** | No authentication — anyone with URL can use it |
| **Authorization** | No user isolation, no role-based access |
| **Credential security** | API tokens in RAM, visible in server logs |
| **Input validation** | CSV size limits, malicious CSV payloads not handled |
| **API rate limits** | No exponential backoff or rate limit handling in connectors |
| **Error boundaries** | Raw exceptions propagated, no user-friendly errors |
| **Monitoring** | No metrics, no alerting, no structured logging |
| **Data retention** | No cleanup of old uploaded files |
| **Compliance** | No GDPR/CCPA handling for email hashing |
| **Webhook support** | No scheduled automatic data pulls |

---

## 5. Test Coverage

**65% overall, but highly uneven.**

| Module | Coverage | Notes |
|--------|----------|-------|
| `ingestion/validators.py` | 100% | ✅ |
| `ingestion/schemas.py` | 100% | ✅ |
| `ingestion/loader.py` | 94% | |
| `ingestion/normalizer.py` | 95% | |
| `engine/search_term_analysis.py` | 100% | ✅ |
| `engine/period_comparison.py` | 94% | |
| `engine/deduplication.py` | High | |
| `engine/cannibalization.py` | High | |
| `engine/incremental_roas.py` | High | |
| `engine/health_checks.py` | High | |
| `engine/user_level_audit.py` | 89% | Lines 161-175 untested |
| **`report/llm_summary.py`** | **0%** | ❌ Entire module untested |
| **`visualization/trend_charts.py`** | **0%** | ❌ Entire module untested |
| **`visualization/dashboard.py`** | **0%** | ❌ Entire module untested |
| **`utils/config.py`** | **0%** | ❌ Entire module untested |
| `visualization/charts.py` | 98% | |

**Critical paths needing tests:**
1. `report/llm_summary.py` — LLM prompt construction and API error paths
2. Connector `fetch_data` methods — pagination, error responses, empty data
3. Search term proportional allocation logic — heuristic, not tested against real edge cases
4. Multi-platform merge — what happens when Meta and Google have overlapping dates?
5. Date parsing edge cases — malformed dates, timezone handling

---

## 6. Technical Debt

1. **Hardcoded assumptions everywhere** — Attribution window (7 days), spend threshold ($5), rolling average (30 days) all in `AuditConfig`. No user visibility.

2. **Zero logging** — No `logging` calls in entire codebase. Debugging production issues = guesswork.

3. **Insufficient error handling** — Most API calls and DataFrame operations throw raw exceptions.

4. **Date parsing fragility** — `pd.to_datetime(mixed=True)` may silently misinterpret ambiguous dates (e.g., `01/02/2024`).

5. **Schema coupling** — Adding TikTok/Pinterest requires code changes in multiple places.

6. **No data versioning** — No way to track which run used which dataset.

7. **`_incremental_per_day` bias** — Takes mean of means across uneven time windows.

---

## 7. Monetizable Product Assessment

### ✅ CAN be extracted and sold today

**Ad Attribution Audit Tool (Aggregate Mode)**
- CSV upload + time-series analysis is functional
- De-dup, cannibalization, ROAS inflation metrics are legitimate insights SMBs care about
- **Positioning:** "Third-party ad verification" — appeals to merchants who distrust platform dashboards
- **Pricing:** Per-report SaaS, $49–299/month depending on data volume

### ❌ Needs significant work before promising

**User-Level Audit** — Email hash matching is inherently limited. Hard sell without proper identity graph (LiveRamp, Adobe Experience Platform level).

**API Connectors** — `test_connection` returns `True` on any HTTP 200. No OAuth2 token refresh. Not robust enough for automated scheduled pulls.

**Search Term Analysis** — Proportional allocation is heuristic, not true matching. Could be misleading and create liability.

### Realistic MVP for monetization

**Product:** Single-tenant (or multi-tenant with strong isolation) Streamlit app on a VPS.

**Core workflow:** Upload CSVs → Run audit → Get PDF/HTML report with key metrics + AI summary.

**Target customer:** Shopify store, $1M–$10M revenue, spending $5K–50K/month on Meta/Google.

**Minimum viable improvements:**
1. Add authentication (Streamlit auth or external auth proxy)
2. Add PDF export (currently HTML only)
3. Add SQLite persistence (audit history)
4. Add LLM executive summary (already wired, needs polish)
5. Harden API connectors with error handling and token refresh

**What to NOT promise:** Real-time monitoring, automated scheduled pulls, pixel-perfect ROAS accuracy.

---

## 8. Code Quality Summary

**Does the code work?** ✅ Yes — for the happy path.
- All 70 tests pass
- Sample data loads and runs successfully
- Aggregate audit pipeline is internally consistent
- Visualization charts render correctly
- HTML export works

**Known/potential bugs:**
1. Email hash collision risk (theoretical for SHA-256 but worth noting)
2. `_incremental_per_day` mean-of-means bias
3. Schema changes silently produce wrong data
4. No error handling for malformed CSV input

**Bottom line:** The core engine is solid. The productionization layer (auth, persistence, error handling, schema versioning) needs significant work before multi-tenant SaaS deployment.

---

*Technical Assessment v1.0 — 2026-04-14*
