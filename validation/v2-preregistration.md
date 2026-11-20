# Validation program v2 preregistration — 2026-11-09

Registered UTC: 2026-11-09T08:32:58.698003+00:00. This document is written before any new estimator,
calibration, sensitivity or test runs in this task. Do not overwrite or backdate it.
Existing Gate-1 outputs were inspected only. No results-informed criteria changes.

## Frozen engine and permitted changes

Freeze the repaired working-tree Python engine, not merely HEAD. Source snapshots
are in `v2-artifacts/frozen-engine/`; SHA-256 hashes follow. Production model:
daily Shopify revenue ~ intercept + six DOW indicators + elapsed-day linear trend
+ all campaign spend columns jointly (spend scaled by its maximum). No month,
GSC, truth controls, carryover or endogenous-demand controls. SVD OLS; HC3
sandwich and two-sided t(n-p) 95% intervals. Existing unidentified-panel guards
remain. The required missing-Shopify-day rejection and new classification/report
fields are correctness changes after this freeze; they must not change complete-
panel coefficients, SEs or intervals. Record final hashes separately. No research
model adjustment is authorized by observing a scenario failure.

## Sampling and scenarios

4,000 independent datasets per scenario; 90 consecutive days from 2026-08-01.
Scenario s, replicate r (0-based) seed = 2026110900 + 100000*s + r, using NumPy
default_rng. Campaign order: Meta Prospecting, Google Generic, Google Brand.
Effects = [4,0.5,0] except S6 [-0.5,0.25,2]. Spend units [100,200,100].
Default spend generator: iid integers 1..4 per day/campaign, independent 18%
pause mask, first seven days all zero, multiplied by spend units. Organic mean
m(t)=50+[0,2,1,3,5,8,6][DOW]+floor(t/30). Mean AOV $100.

- S1: exact documented original fixture at daily sufficient-statistic level:
  original spend draws followed by iid integer organic noise -2..2; orders =
  m(t)+noise+spend@effect/100; revenue=100*orders. No RNG draws interposed.
- S2: same spend; N(t)~Poisson(m(t)+spend@effect/100). Each of the N orders has
  independent lognormal value with mean100, CV0.8 (sigma=sqrt(log(1+0.8^2)),
  mu=log(100)-sigma^2/2). Sum individual order values, not a daily AOV proxy.
- S3: as S2, but independent five-day spend blocks (18 blocks, original level
  and pause distribution, repeat each five times; first seven days zero).
  Add 100*u(t) to daily revenue, where stationary Gaussian AR(0.5) u has SD
  sqrt(65), innovation SD sqrt(65*(1-0.5^2)), initial u0~N(0,65).
  This is an additive residual-demand stress at Poisson order scale on top of
  compound-Poisson revenue, not integer order generation for the AR component.
- S4: draw original spend first, then latent daily demand z~N(0,8^2).
  Replace Brand spend by clip(200+20*z,0,400), first seven days zero.
  Organic mean=max(1,m(t)+z); Poisson counts and order values as S2. This is
  demand-driven endogenous Brand spend at true causal effect zero. Record any
  organic floor activations; no selection or rerolling of extreme datasets.
- S5: as S2 with Meta revenue input replaced by normalized adstock
  a(t)=0.5*spend_Meta(t)+0.5*a(t-1), a(-1)=0. Long-run cumulative truth 4x;
  same-day coefficient is deliberately misspecified. The horizon omits the
  carryover tail after day90; evaluate against long-run truth, not 2x.
- S6: S2 with effects [-0.5,+0.25,2.0]. No clipping of negative estimated effects.

Truth is used only by generator/evaluator, never production fit inputs. The
in-process estimator is called once per dataset; no per-dataset CLI or pytest.
Save each replicate's coefficients, SEs, CIs, labels, and seed for auditability.

## Labels and metrics

Delta=0.2x. Exclusive label precedence: unavailable for absent/nonfinite CI;
practically zero if the full CI is inside [-0.2,+0.2] (inclusive); otherwise
positive if lower>0; otherwise negative if upper<0; otherwise inconclusive.
Equivalence takes precedence for narrow nonzero intervals inside the practical
region; this resolves overlap before observing results. Truth classes use the
same practical region: |truth|<=0.2 practically zero, else sign. Legacy binary
flag = CI includes zero, reported only for comparison.

For every campaign/scenario: signed bias, RMSE, mean SE, |bias|/mean SE, empirical
95% coverage, exact two-sided 95% Clopper-Pearson lower coverage bound
(Beta quantile 0.025, k,n-k+1; zero when k=0), median CI width, all five label
rates, legacy flag rate, false-flag rate (practically zero OR negative), and
unavailable rate. Coverage denominator = all 4,000 datasets (unavailable counts
as noncoverage); estimate/SE/width metrics conditional on availability with n
printed. Confusion rows = true campaign class versus all emitted labels.

80%-power MDE per fitted SE: solve for noncentrality d>=0 such that
P(|T_df(noncentrality=d)|>t_df(.975))=.8, multiply d*SE. Report median and
10th/90th percentiles; this is model-based detection versus zero, not equivalence
power or a correction for bias/serial correlation. Use each fit's residual df.

## Frozen pass criteria

Per campaign, per scenario unless explicitly scoped:
1. Coverage exact CP lower bound >=0.92 in S1 and S2 only. S3-S6 coverage is
   descriptive and cannot silently become an extra pass requirement.
2. |bias| <=0.1*mean SE in every scenario.
3. For true effects >=0.25x, false-flag rate <=10% under the new labels.
4. For zero truth in S1/S2, positive-label rate <=10%. Report zero positive
   rates in S3-S5 without applying this as a stress gate.
Scenario PASS only if all applicable campaign criteria pass; FAIL is informative.
No familywise adjustment; these are marginal campaign criteria. Finite Monte
Carlo uncertainty remains; no reruns or sample-size changes to rescue a failure.

## Inference comparison, sensitivity, and report changes

On identical S2/S3 panels compare production HC3-t with Bartlett Newey-West
HAC lag4 and lag7, OLS residual scores, finite-sample factor n/(n-p), t(n-p)
critical values. Report coverage, CP lower and median width per campaign. Keep
production HC3 unless a candidate has coverage no lower AND median width no
larger in EVERY campaign in BOTH scenarios (at least one strict improvement).
If both dominate choose lag7. Any swap requires a versioned change and before/
after numbers; no changes to pass criteria.

On final code, for original seeds 20261108..20261112, reconstruct the exact S1
fixture, cross-check saved daily panels, and fit DOW+trend, DOW+month+trend,
and DOW+true-steps+trend (indicators t>=30,t>=60). Reuse final feature builder;
truth steps are sensitivity only. Print all estimates and Brand month-minus-
base gaps. Compare reported historical Brand month0.146670 and gap~0.132.
Do not infer the mid-repair cause if not demonstrated.

Correctness fixes: mark missing Shopify calendar dates inside the observed
Shopify min/max (including dates absent from every source) as explicit data-
quality failures for campaigns; keep legacy numeric compatibility only with
result warnings. PDF receives contribution_margin; omitted/None means assumed
0.40 with threshold2.5x, explicitly unknown customer margin and actions labeled
"revenue-iROAS priorities, not profit decisions". A supplied finite margin must
be >0 and <=1. Actions use CI versus 1/margin, never stale stored actions.
Update sample validation language so five-seed PASS is not shown as v2 evidence.

Run full pytest after changes; save count/log and PDF evidence. No commits,
pushes, external account writes, or edits to historical validation claims.

## Frozen source SHA-256

- `ad_audit/engine/__init__.py`: `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`
- `ad_audit/engine/aggregate_audit.py`: `c1953f9d7f6096a9b2532cea65c44871dace81aba136fc1bcd6f34a98784575f`
- `ad_audit/engine/campaign_regression.py`: `9198bad4b4955e04f779ba596cff36e88eb7970c1694dd874b2f6d43e73b15a6`
- `ad_audit/engine/cannibalization.py`: `4976375badd59f1fa0058c1831860049094c6bdf05dc66a38795b0d00c05dd3d`
- `ad_audit/engine/deduplication.py`: `da88ba2dd9ffac05ae4045e635738dc32dc132ce718e99336b58b8ee21e0d102`
- `ad_audit/engine/health_checks.py`: `463fa12d8f53d00fc6cfcd1f6df35f5fa4396aaf599d1e69b0c7e8d74c7f2f2a`
- `ad_audit/engine/incremental_roas.py`: `c1eb6965a6ebe5622e8ccb3b4efa966c513f101007b5a2eadd54824090dcd8b4`
- `ad_audit/engine/models.py`: `1a66cdc4c4fd2965d59d98eaad656fd81a5ea8a28c36367edd3035d4d11bfc9c`
- `ad_audit/engine/organic_baseline_regression.py`: `1965350e78f4c9d6299a1d9e111207d39d763215870658cc377d65d7ec2ff14b`
- `ad_audit/engine/period_comparison.py`: `96651f668055970276b88c1e3fb09fa4bf58e9c411d8016d58b0be609f64054b`
- `ad_audit/engine/search_term_analysis.py`: `d0c19742da8bffc307665e34a9fab407192555f991a80c39bc4a4a278d454340`
- `ad_audit/engine/user_level_audit.py`: `f41860a2fb6553b6298d58870dc58334dfc73825595e295dc59a2177ade317ac`
