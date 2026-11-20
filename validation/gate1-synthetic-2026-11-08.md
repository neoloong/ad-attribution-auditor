# Quality Gate 1 — synthetic ground-truth validation — 2026-11-08

**Verdict: FAIL.** The unchanged Python engine runs end to end, but it cannot provide validated campaign-level incrementality or confidence intervals. Campaign-filtered values below are actual engine outputs; they are diagnostics against the same full-store Shopify orders, not identified campaign effects. No truth labels or counterfactual orders entered the engine.

## Reproduce and execution evidence

```sh
.venv/bin/python scripts/run_gate1_validation.py
```

The script runs pytest first, regenerates the inputs and both deliverables, verifies fixture conservation, and exits 1 for a failed quality gate after producing the artifacts. It uses no accounts, network requests, or paid services. PDF rendering uses the standard library.

- Baseline tests: 170 passed in 0.58s (exit 0); full output in `gate1-synthetic-2026-11-08/pytest.txt`.
- Engine revision: `9bf3954f58cbbf4a188e1ca48ac6893724674c3f`; working tree was clean before this task.
- Python 3.12.16; package versions recorded in `results.json`.

## Inspected entry points and existing fixtures

- `ad_audit/engine/aggregate_audit.py:run_aggregate_audit`: production Python aggregate pipeline, called by `pages/2_Run_Audit.py` after concatenating Meta and Google rows.
- `ad_audit/engine/user_level_audit.py:run_user_level_audit`: separate click-matching heuristic; not used for this aggregate OLS validation.
- `scripts/generate_mock_data.py` and `data/sample_*.csv`: existing 60-day demo fixtures, without coherent per-campaign causal truth. Left unchanged.
- `web/src/lib/engine/aggregate-audit.ts`: separate browser implementation, not executed here.
- `ad_audit/report/html_export.py:export_html_report`: existing HTML export only. This task adds a local PDF renderer; it does not modify the application UI.

## Dataset design

Seed **20261108**; **90 consecutive days**, 2026-08-01 through 2026-10-29. One store; three campaigns; 5,797 individual orders, each worth $100.00. There are 7 common zero-spend days, including the first seven.

Spend is independently randomized per campaign over four positive levels, with an additional 18% independent pause probability, then a shared initial seven-day pause. Meta and Brand levels are $100/$200/$300/$400; Generic levels are $200/$400/$600/$800. These are fixture design parameters, not estimated performance. Organic orders = 50 + day-of-week effects [0,2,1,3,5,8,6] (Monday first) + floor(day_index/30) + seeded integer noise in [-2,2]. Incremental orders = spend × known causal ROAS / $100, exactly integral for these levels. Orders = organic + all incremental orders. No lag, saturation, price variation, refunds, cross-campaign interactions, or missing dates: this is an intentionally favorable linear test.

Removing one campaign removes only its generated incremental orders; organic demand and other campaigns stay fixed. Brand causes no orders but claims organic orders at 8x ROAS. Its daily claims never exceed available organic orders, and those orders carry misleading brand last-click UTMs. Meta claims 5x and Generic 3x. GSC clicks = 100 + 4 × (organic_orders − 50) + 3 × brand_claims; impressions = clicks × 10. Search activity can rise without generating additional orders.

Actual organic total: 4,920; daily mean 54.666667. Daily/order truth ledgers are separate from the four uploaded CSVs. Schema validation, normalization, order IDs, daily counts, revenue, and causal-order conservation all passed.

## Known ground truth

| Campaign | Truth class | Spend | Causal orders | Causal revenue | True iROAS | Claimed orders | Platform ROAS |
|---|---|---:|---:|---:|---:|---:|---:|
| Meta Prospecting | HIGH | $18,100.00 | 724 | $72,400.00 | 4.0000x | 905 | 5.0000x |
| Google Generic | LOW | $30,600.00 | 153 | $15,300.00 | 0.5000x | 918 | 3.0000x |
| Google Brand | ZERO | $16,800.00 | 0 | $0.00 | 0.0000x | 1344 | 8.0000x |

## Actual engine estimates and errors

**Combined store run:** spend $65,500.00; reported revenue $316,700.00; reported ROAS 4.8351x; estimated incremental revenue $93,700.00; estimated iROAS 1.4305x. Known combined iROAS 1.338931x; absolute error 0.091569x. Baseline method `timeseries_interruption`; estimated organic daily orders 54.000000.

**Campaign diagnostics:** call the same engine three more times, filtering only the ad rows by campaign while retaining the same full-store Shopify and GSC inputs and all 90 dates. The engine sums ad rows by date and discards campaign identity. It never allocates total-store orders among campaigns. Consequently, each diagnostic is confounded by other campaigns; these are not three additive campaign estimates. They expose the missing capability, rather than adding an unrequested replacement estimator.

Thresholds declared in code before running: point estimate absolute error ≤ max(0.10x, 20% of positive true iROAS). At zero truth relative error is undefined; use ≤ 0.10x absolute error plus a non-incrementality signal (estimate ≤ 0.10x and an inflation/cannibalization health warning). Full campaign PASS additionally requires supported campaign attribution and a supplied confidence interval containing truth. Missing capabilities fail the gate. The engine has no CI level or bounds, so coverage is **unavailable**, not false or 0%.

| Campaign | Estimated iROAS (diagnostic) | Abs. error | Rel. error | Point check | CI / covers truth | Campaign gate |
|---|---:|---:|---:|---|---|---|
| Meta Prospecting | 4.7956x | 0.7956x | 19.89% | PASS | unavailable / not assessable | FAIL |
| Google Generic | 2.5850x | 2.0850x | 417.00% | FAIL | unavailable / not assessable | FAIL |
| Google Brand | 3.7202x | 3.7202x | undefined (truth = 0) | FAIL | unavailable / not assessable | FAIL |

| Run | Baseline method | Baseline orders/day | R² | Cannibalization score | Health alert titles |
|---|---|---:|---:|---:|---|
| Combined | timeseries_interruption | 54.000000 | 0.000000 | 48.19% | Severe ROAS Inflation; High Cannibalization |
| Meta Prospecting | timeseries_interruption | 54.000000 | 0.000000 | 37.88% | Elevated Cannibalization |
| Google Generic | timeseries_interruption | 54.000000 | 0.000000 | 41.54% | High Cannibalization; Weak Spend-Conversion Correlation |
| Google Brand | timeseries_interruption | 55.500000 | 0.000000 | 62.12% | High Cannibalization; Negative Spend-Conversion Correlation; ROAS Inflation Detected |

The production OLS attempt was rejected in every run; the router then used a spend-off interruption baseline. R² = 0 in the table denotes the non-regression fallback, not the rejected model's fit. Re-running the same OLS helper on each saved merged input records these rejection reasons (also in `results.json`):

- Combined: Poor model fit: R² = -3.4832 < 0.01
- Meta Prospecting: Poor model fit: R² = -3.5215 < 0.01
- Google Generic: Poor model fit: R² = -4.6867 < 0.01
- Google Brand: Poor model fit: R² = -4.9072 < 0.01

**Zero campaign detection:** combined numeric/warning proxy = **False** for Google Brand. There is no explicit campaign-level non-incremental flag in the engine. A generic inflation/cannibalization warning is recorded separately in `results.json`; it cannot certify causal non-incrementality or rescue missing intervals/attribution.

## Findings, changes, and limitations

No execution blockers: all baseline tests passed and ingestion, normalization, aggregate audit, health checks, and local PDF generation completed. **No production engine code was changed.** This preserves the engine under test and avoids silently turning a validation task into a statistical-model rewrite.

Inspection found these model limitations (not repaired):

1. `_build_features` in `organic_baseline_regression.py` has no constant column. The caller treats `beta[0]` (the normalized spend coefficient) as an intercept and also uses it as the ad marginal effect. This does not fit the documented intercept model.
2. Trend is normalized to [0,1], but `_compute_baseline_from_coeffs` multiplies its coefficient by (n−1)/2 rather than 0.5. DOW/month effects average only included dummy coefficients rather than actual zero-spend predictions over the observation dates. The resulting baseline need not be a valid organic counterfactual.
3. `compute_incremental_roas` clips negative incremental revenue to zero. An excessive baseline can therefore create a convincing-looking zero even for an incremental campaign. It is not an estimate of a campaign spend coefficient.
4. `AuditResult`/`IncrementalROASResult` contain neither campaign estimates nor interval bounds. The existing tests do not establish the causal recovery requested by this gate.

The gate fails even in this favorable linear synthetic setting. A single seeded dataset does not measure repeated-sampling coverage, robustness, or real-world causality. Observational associations, GSC overlap, and aggregate order counts alone do not establish incrementality. Customer-facing campaign budget decisions require a repaired estimator, uncertainty estimates, and a controlled holdout or equivalent design.

## Customer sample

PDF: `sample/sample-report-2026-11-08.pdf`. Every page is labeled **SAMPLE — synthetic data**. It uses the engine outputs stored in `results.json`; missing confidence intervals are explicitly unavailable. All campaign actions are KEEP under a validation hold. No automatic kill or scale recommendation can be justified by a failed model. The known causal ROAS values are used only in this validation memo, not as substitutes for engine estimates in the customer report.

## Artifacts

- `validation/gate1-synthetic-2026-11-08/`: four input CSVs, two truth ledgers, four merged engine daily CSVs, baseline pytest log, results JSON with all point estimates, alerts, errors, versions, and input SHA-256 hashes.
- `scripts/run_gate1_validation.py`: deterministic dataset, production-engine execution, evaluation, and Markdown generation.
- `scripts/gate1_pdf.py`: standalone local PDF generation from actual outputs.
- `scripts/verify_gate1_pdf.swift`: independent macOS PDFKit parsing and raster previews. Run `swift -module-cache-path /tmp/gate1-swift-cache scripts/verify_gate1_pdf.swift` after generation. It checks every page label and all table ROAS figures and writes `pdf-verification.json`; previews/text go to `/tmp/ad-auditor-gate1-preview-2026-11-08/`.
- `files-created.txt`: exhaustive list of created repository artifacts; no pre-existing files changed.
- No commits or pushes performed.
