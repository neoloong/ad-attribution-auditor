# Validation program v2 — 2026-11-09

The unqualified Gate-1 PASS is withdrawn. All numbers below are actual in-process runs against the immutable [preregistration](v2-preregistration.md). No pass criteria or sample sizes changed.

Executed 2026-11-09T08:36:51.940621+00:00 to 2026-11-09T08:37:19.058564+00:00; 4,000 datasets per scenario, 24,000 total. Three campaigns per dataset; 95% marginal intervals. No commits or pushes.

Reproduce: `.venv/bin/python scripts/run_v2_validation.py`. Full-suite evidence: `v2-artifacts/pytest.txt`. Raw replicate results: `v2-artifacts/replicates.csv`; summary/metadata/hashes: `v2-artifacts/results.json`; specs: `v2-artifacts/spec-gap.csv`.

## Verdicts against the preregistered criteria

| Scenario | Verdict | Failed campaign criteria |
|---|---|---|
| S1 | FAIL | Meta Prospecting: bias; Google Generic: bias; Google Brand: bias |
| S2 | PASS | None |
| S3 | PASS | None |
| S4 | FAIL | Meta Prospecting: bias; Google Generic: bias; Google Brand: bias |
| S5 | FAIL | Meta Prospecting: bias; Google Generic: bias; Google Brand: bias |
| S6 | PASS | None |

Coverage CP bounds apply only to S1/S2; bias applies in every scenario; false flags apply at truth >=0.25x; zero-positive error is gated only in S1/S2. Stress coverage and zero-positive rates remain visible below. No thresholds were weakened to grant a PASS.

**S3 PASS does not mean calibrated intervals**: its coverage is below nominal and is not a preregistered stress pass condition. S1 fails all three bias checks (0.115–0.144 mean SE) despite adequate coverage. S2 alone passes the full coverage/bias/classification calibration criteria. No production model was tuned to repair these outcomes.

## Calibration and stress metrics

All effect/width/SE/MDE units are revenue dollars per ad dollar (x). Coverage denominator includes unavailable fits; point/SE/width metrics condition on availability. CP lower is the exact two-sided 95% Clopper-Pearson lower endpoint. Bias/SE is absolute.

### S1: original low-noise fixture

| Campaign (truth) | Available/N | Bias | RMSE | Mean SE | Abs bias/SE | Coverage | CP lower | Median width | MDE80 median [p10,p90] |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| Meta Prospecting (+4) | 4000/4000 | -0.01414 | 0.11317 | 0.12263 | 0.115 | 96.75% | 96.15% | 0.4861 | 0.3463 [0.3055,0.3912] |
| Google Generic (+0.5) | 4000/4000 | -0.00882 | 0.05906 | 0.06128 | 0.144 | 95.50% | 94.81% | 0.2430 | 0.1731 [0.1532,0.1956] |
| Google Brand (+0) | 4000/4000 | -0.01499 | 0.11631 | 0.12251 | 0.122 | 96.23% | 95.59% | 0.4858 | 0.3461 [0.3063,0.3910] |

| Campaign / truth class | Positive | Negative | Practically zero | Inconclusive | Unavailable | Flag rate | Legacy flag |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Meta Prospecting / positive | 100.00% | 0.00% | 0.00% | 0.00% | 0.00% | 0.00% | 0.00% |
| Google Generic / positive | 100.00% | 0.00% | 0.00% | 0.00% | 0.00% | 0.00% | 0.00% |
| Google Brand / practically_zero | 1.32% | 2.45% | 0.10% | 96.12% | 0.00% | 2.55% | 96.23% |

### S2: compound Poisson orders, lognormal values CV0.8

| Campaign (truth) | Available/N | Bias | RMSE | Mean SE | Abs bias/SE | Coverage | CP lower | Median width | MDE80 median [p10,p90] |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| Meta Prospecting (+4) | 4000/4000 | -0.02802 | 0.82006 | 0.87088 | 0.032 | 96.33% | 95.69% | 3.4165 | 2.4341 [2.0858,2.8822] |
| Google Generic (+0.5) | 4000/4000 | -0.00755 | 0.40257 | 0.43421 | 0.017 | 96.35% | 95.72% | 1.7124 | 1.2200 [1.0473,1.4281] |
| Google Brand (+0) | 4000/4000 | -0.01332 | 0.80951 | 0.86757 | 0.015 | 96.05% | 95.40% | 3.4247 | 2.4400 [2.0874,2.8580] |

| Campaign / truth class | Positive | Negative | Practically zero | Inconclusive | Unavailable | Flag rate | Legacy flag |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Meta Prospecting / positive | 99.62% | 0.00% | 0.00% | 0.38% | 0.00% | 0.00% | 0.38% |
| Google Generic / positive | 18.15% | 0.03% | 0.00% | 81.83% | 0.00% | 0.03% | 81.83% |
| Google Brand / practically_zero | 1.93% | 2.02% | 0.00% | 96.05% | 0.00% | 2.02% | 96.05% |

### S3: five-day flights plus AR(0.5) residual shocks

| Campaign (truth) | Available/N | Bias | RMSE | Mean SE | Abs bias/SE | Coverage | CP lower | Median width | MDE80 median [p10,p90] |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| Meta Prospecting (+4) | 4000/4000 | -0.02161 | 1.37192 | 1.19002 | 0.018 | 91.35% | 90.44% | 4.5825 | 3.2648 [2.6503,4.2204] |
| Google Generic (+0.5) | 4000/4000 | -0.01984 | 0.67317 | 0.59450 | 0.033 | 92.00% | 91.12% | 2.3039 | 1.6414 [1.3189,2.0984] |
| Google Brand (+0) | 4000/4000 | 0.00572 | 1.38596 | 1.19068 | 0.005 | 90.85% | 89.91% | 4.6102 | 3.2845 [2.6335,4.2463] |

| Campaign / truth class | Positive | Negative | Practically zero | Inconclusive | Unavailable | Flag rate | Legacy flag |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Meta Prospecting / positive | 87.38% | 0.00% | 0.00% | 12.62% | 0.00% | 0.00% | 12.62% |
| Google Generic / positive | 15.93% | 0.68% | 0.00% | 83.40% | 0.00% | 0.68% | 83.40% |
| Google Brand / practically_zero | 4.38% | 4.78% | 0.00% | 90.85% | 0.00% | 4.78% | 90.85% |

### S4: demand-driven endogenous Brand spend

| Campaign (truth) | Available/N | Bias | RMSE | Mean SE | Abs bias/SE | Coverage | CP lower | Median width | MDE80 median [p10,p90] |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| Meta Prospecting (+4) | 4000/4000 | -0.57506 | 1.03088 | 0.92551 | 0.621 | 92.10% | 91.22% | 3.6556 | 2.6045 [2.2219,3.0496] |
| Google Generic (+0.5) | 4000/4000 | -0.30314 | 0.52094 | 0.46009 | 0.659 | 91.83% | 90.93% | 1.8147 | 1.2929 [1.1058,1.5182] |
| Google Brand (+0) | 4000/4000 | 5.27517 | 5.35686 | 1.00431 | 5.253 | 0.05% | 0.01% | 3.9585 | 2.8203 [2.3961,3.3348] |

| Campaign / truth class | Positive | Negative | Practically zero | Inconclusive | Unavailable | Flag rate | Legacy flag |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Meta Prospecting / positive | 95.83% | 0.00% | 0.00% | 4.17% | 0.00% | 0.00% | 4.17% |
| Google Generic / positive | 5.00% | 0.47% | 0.00% | 94.53% | 0.00% | 0.47% | 94.53% |
| Google Brand / practically_zero | 99.95% | 0.00% | 0.00% | 0.05% | 0.00% | 0.00% | 0.05% |

### S5: normalized Meta adstock lambda0.5, long-run target4x

| Campaign (truth) | Available/N | Bias | RMSE | Mean SE | Abs bias/SE | Coverage | CP lower | Median width | MDE80 median [p10,p90] |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| Meta Prospecting (+4) | 4000/4000 | -1.84931 | 2.02969 | 0.88060 | 2.100 | 44.82% | 43.28% | 3.4674 | 2.4704 [2.1242,2.8985] |
| Google Generic (+0.5) | 4000/4000 | 0.08462 | 0.41846 | 0.44003 | 0.192 | 95.78% | 95.10% | 1.7397 | 1.2395 [1.0559,1.4543] |
| Google Brand (+0) | 4000/4000 | 0.16304 | 0.84295 | 0.87960 | 0.185 | 96.00% | 95.35% | 3.4702 | 2.4723 [2.1011,2.9120] |

| Campaign / truth class | Positive | Negative | Practically zero | Inconclusive | Unavailable | Flag rate | Legacy flag |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Meta Prospecting / positive | 67.73% | 0.00% | 0.00% | 32.27% | 0.00% | 0.00% | 32.27% |
| Google Generic / positive | 24.40% | 0.00% | 0.00% | 75.60% | 0.00% | 0.00% | 75.60% |
| Google Brand / practically_zero | 2.62% | 1.38% | 0.00% | 96.00% | 0.00% | 1.38% | 96.00% |

### S6: S2 noise, signed/boundary effects

| Campaign (truth) | Available/N | Bias | RMSE | Mean SE | Abs bias/SE | Coverage | CP lower | Median width | MDE80 median [p10,p90] |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| Meta Prospecting (-0.5) | 4000/4000 | -0.00797 | 0.76486 | 0.82662 | 0.010 | 96.60% | 95.99% | 3.2609 | 2.3233 [1.9787,2.7279] |
| Google Generic (+0.25) | 4000/4000 | -0.00908 | 0.39044 | 0.41417 | 0.022 | 95.67% | 95.00% | 1.6351 | 1.1649 [0.9910,1.3722] |
| Google Brand (+2) | 4000/4000 | -0.03107 | 0.78158 | 0.82978 | 0.037 | 96.58% | 95.96% | 3.2786 | 2.3359 [1.9796,2.7448] |

| Campaign / truth class | Positive | Negative | Practically zero | Inconclusive | Unavailable | Flag rate | Legacy flag |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Meta Prospecting / negative | 0.27% | 7.92% | 0.00% | 91.80% | 0.00% | 7.92% | 91.80% |
| Google Generic / positive | 7.27% | 0.40% | 0.00% | 92.33% | 0.00% | 0.40% | 92.33% |
| Google Brand / positive | 66.07% | 0.00% | 0.00% | 33.92% | 0.00% | 0.00% | 33.92% |

These rows are the four-label confusion rates by truth class (plus unavailable). Equivalence takes precedence when a narrow interval both excludes zero and lies inside the practical region. Flag rate means practically zero OR negative; it is a false flag only for true effects >=0.25x. Legacy means CI includes zero. A wide interval is inconclusive and can have low false-flag rate while providing little decision power. MDE80 uses noncentral-t two-sided power and each observed SE; it cannot repair bias or invalid SEs.

The realistic-noise S2 Generic campaign (true 0.5x) receives the legacy zero-in-CI flag 81.83% of the time, while the new false-flag rate is 0.025% and the inconclusive rate 81.825%. Its median 80%-power detection threshold is 1.2200x. The four-label scheme avoids interpreting weak power as proof of zero effect; it does not make the 90-day panel precise. S6 similarly has 91.80% inconclusive labels for the true -0.5x effect and 92.325% for true +0.25x.

## Inference comparison on paired datasets

| Scenario | Campaign | Method | Coverage | CP lower | Median width |
|---|---|---|---:|---:|---:|
| S2 | Meta Prospecting | HC3 | 96.33% | 95.69% | 3.4165 |
| S2 | Meta Prospecting | HAC4 | 93.42% | 92.61% | 3.0418 |
| S2 | Meta Prospecting | HAC7 | 92.27% | 91.40% | 2.9529 |
| S2 | Google Generic | HC3 | 96.35% | 95.72% | 1.7124 |
| S2 | Google Generic | HAC4 | 93.12% | 92.30% | 1.5212 |
| S2 | Google Generic | HAC7 | 92.20% | 91.33% | 1.4794 |
| S2 | Google Brand | HC3 | 96.05% | 95.40% | 3.4247 |
| S2 | Google Brand | HAC4 | 92.92% | 92.09% | 3.0443 |
| S2 | Google Brand | HAC7 | 91.80% | 90.91% | 2.9518 |
| S3 | Meta Prospecting | HC3 | 91.35% | 90.44% | 4.5825 |
| S3 | Meta Prospecting | HAC4 | 88.67% | 87.65% | 4.3744 |
| S3 | Meta Prospecting | HAC7 | 87.52% | 86.46% | 4.2548 |
| S3 | Google Generic | HC3 | 92.00% | 91.12% | 2.3039 |
| S3 | Google Generic | HAC4 | 89.60% | 88.61% | 2.1858 |
| S3 | Google Generic | HAC7 | 88.38% | 87.34% | 2.1293 |
| S3 | Google Brand | HC3 | 90.85% | 89.91% | 4.6102 |
| S3 | Google Brand | HAC4 | 88.65% | 87.63% | 4.4004 |
| S3 | Google Brand | HAC7 | 87.38% | 86.31% | 4.2801 |

Production inference swap: **NO; HC3 retained**. Dominance required coverage no lower AND width no greater for every campaign in both scenarios. HAC uses Bartlett weights, n/(n-p) correction and t(n-p). Neither interval method repairs endogenous spend or omitted carryover.

## Final-code specification gap

The exact original five daily fixtures were reconstructed and compared to saved Gate-1 panels (spend, orders, revenue and platform revenue match exactly). The true-step sensitivity adds t>=30 and t>=60 to DOW+trend; it is not a deployable model selection recommendation. All point estimates below use final feature code.

| Seed | Spec | Meta | Generic | Brand |
|---|---|---:|---:|---:|
| 20261108 | DOW+trend | 3.947268 | 0.503307 | 0.014224 |
| 20261108 | DOW+month+trend | 4.055387 | 0.519118 | 0.146670 |
| 20261108 | DOW+steps+trend | 4.044971 | 0.514832 | 0.126025 |
| 20261109 | DOW+trend | 3.939789 | 0.436847 | -0.073732 |
| 20261109 | DOW+month+trend | 3.928480 | 0.435248 | -0.075938 |
| 20261109 | DOW+steps+trend | 3.914426 | 0.435172 | -0.077723 |
| 20261110 | DOW+trend | 4.071617 | 0.617558 | 0.055980 |
| 20261110 | DOW+month+trend | 4.093610 | 0.622486 | 0.066587 |
| 20261110 | DOW+steps+trend | 4.097482 | 0.615434 | 0.061563 |
| 20261111 | DOW+trend | 3.884729 | 0.563507 | 0.013581 |
| 20261111 | DOW+month+trend | 3.901696 | 0.568668 | 0.006577 |
| 20261111 | DOW+steps+trend | 3.903036 | 0.575703 | -0.004080 |
| 20261112 | DOW+trend | 4.032365 | 0.590397 | -0.122509 |
| 20261112 | DOW+month+trend | 4.024067 | 0.633302 | -0.085088 |
| 20261112 | DOW+steps+trend | 4.021411 | 0.637470 | -0.066306 |

| Seed | Brand month minus base |
|---|---:|
| 20261108 | +0.132447x |
| 20261109 | -0.002206x |
| 20261110 | +0.010607x |
| 20261111 | -0.007004x |
| 20261112 | +0.037421x |

Original seed final-code Brand: base 0.014224x; month 0.146670x (95% CI [-0.092067, 0.385407]); gap +0.132447x. The historical 0.146670x month estimate and approximately 0.132x gap **reproduce on final code**. The proposed mid-repair-code explanation is not supported by this rerun; the historical sensitivity numbers need no correction.

An explanatory linear decomposition of these same original-seed fits separates the known organic mean, the true campaign signal, and the realized integer noise. The Brand gap is +0.052113x from the deterministic organic component plus +0.080334x from the realized noise. The true campaign signal contributes zero to this gap. Conditional on this observed spend design, the exact SD of the noise contribution is 0.041777x: sqrt(2)*100 times the norm of the difference between the two Brand OLS coefficient-weight vectors. Thus this realized noise contribution is 1.92 conditional SDs from its expectation. The omitted floor(day/30) steps and this particular spend design explain why a marginal gap SD around 0.028 cannot be used as the conditional SD around zero for this seed. This decomposition explains existing fits; it adds no pass criterion or fitted production control. Component values are in spec-gap.csv.

## What is calibrated, what must warn, what is unavailable

The complete, identified, exogenous, immediate linear-effect S2 design passes the preregistered calibration criteria at the tested spend/noise scale. S1 has sufficient coverage but fails the bias tolerance; it is not a full calibration PASS. S6 separately audits signed and 0.25x boundary behavior. No scenario certifies causal effects from an arbitrary observational store.

Always warn that causal interpretation needs exogenous spend and a valid outcome model. Flighted spend with serial shocks, demand-driven spend, and carryover must warn; their numerical failures cannot be converted into customer budget decisions. The existing Durbin-Watson warning is imperfect: absence of an autocorrelation warning does not establish exogeneity or an immediate-response model. These stress conditions are not automatically identifiable from this panel alone; independent design/domain checks or controlled holdouts are necessary.

Campaign inference must return unavailable for missing interior Shopify days, gapped or duplicate dates, fewer than 60 days, absent campaign identity, zero-spend campaigns, rank deficiency/ill-conditioning, invalid revenue/spend, insufficient residual df, or unit leverage. Missing order rows cannot establish a verified zero-order day. The legacy store fallback remains uncalibrated, with null CI and explicit data-quality warnings in result.extras. Missing dates outside all observed exports remain unknowable.

## Correctness changes and evidence

Missing Shopify calendar days are detected before zero filling, including dates missing from all exports. The campaign point, CI and new label remain unavailable; legacy store behavior surfaces the reason through data_quality_warnings. Tests cover Shopify-only gaps, gaps absent from every export, and complete-panel inference.

The PDF computes break-even iROAS=1/contribution margin and recomputes actions from intervals. Unknown margin defaults to an explicitly assumed 40%, threshold 2.50x, with actions labeled "revenue-iROAS priorities, not profit decisions". Supplied margins must be finite in (0,1]. The regenerated sample uses final-engine original-fixture outputs, four-label evidence, a validation hold, and v2 limitations; stale five-seed actions and PASS language are superseded.

Frozen/current complete-panel numerical equivalence checked: 60 panels across all six scenarios, exactly identical points/SEs/CIs. Source/preregistration hashes and software versions are saved in results.json. Only correctness/classification changes were made to the estimator; HC3 is retained.

S4 organic-floor activations: 0. This study instantiates specified stresses and is not a claim to reproduce the independent reviewers' exact percentages from their unspecified random streams.

Final test count, PDF verification and changed-file manifest are recorded in `v2-artifacts/completion.json` after the full suite and artifact checks.

## Final verification and changed files

214 passed in 0.91s (full suite, exit 0). The macOS PDFKit parser verified all three sample labels, displayed point estimates and CIs, the margin assumption, threshold and priority limitation. The action and methodology pages were visually inspected. Raw replicate aggregates, CP bounds and source hashes were independently checked against saved results.

All task changes (including frozen source snapshots and raw outputs) are listed in [files-changed.txt](v2-artifacts/files-changed.txt). Pre-existing working-tree changes were preserved; unrelated Gate-1 engine repairs are not claimed as v2 changes. The preregistration SHA-256 and original filesystem modification time remain unchanged.
