# Acceptance — agent-native MCP prototype (2026-11-13/14 UTC)

**Verdict: PASS** for validate / run / report. Acceptance of record is **run 2** (after one starter-prompt
fix found in run 1). Full transcripts: [`acceptance-transcript.txt`](acceptance-transcript.txt); raw
stream-json logs and the exact prompts sent: `raw/run1/`, `raw/run2/`.

## Setup (simulated stranger)

- Fresh `claude -p` sessions (Claude Code 2.1.319, model `claude-opus-5-5`) in scratch directories
  `/tmp/aaa-stranger-Eajf` (run 1) and `/tmp/aaa-stranger2-*` (run 2) — not the repo, no repo CLAUDE.md.
- MCP config registering **only** this server (`raw/run*/auditor-mcp.json`), with `--strict-mcp-config`,
  `--tools ""` (all built-in tools removed: no Bash, Read, Grep, Edit…) and
  `--allowedTools mcp__ad-attribution-auditor`. The session-init event confirms the session's only tools
  were `validate_csv`, `run_audit`, `get_report` and the server was `connected`.
- Turn 1 input = the entire `STARTER_PROMPT.md` + the three sample file paths, nothing else.
  Turn 2 (`--resume`) = the stranger's answers to the agent's questions: "I don't know my margin, use the 40%
  assumption. The zero-spend gaps are real … The emails are fake demo data, so go ahead as is. Please run the
  audit and give me the report."
- Files used: the repo samples, all of which pass the current loaders:
  `data/sample_meta_ads.csv`, `data/sample_google_ads.csv`, `data/sample_shopify_orders.csv`.
  The copies in `/Users/chao/dev/auditor-demo/demo/samples/` are **not** copies of these — they are a
  different, newer-looking schema (`date,campaign_name,spend,purchases,…,currency,timezone`) that the current
  loaders would reject for missing headers. They were not used.

## Results per step (run 2)

| Step | Result | Evidence |
|---|---|---|
| Validate | **PASS** | 3 × `validate_csv` (by `path`), all `ok: true`. Agent relayed every warning (one campaign row per day → missing campaign-days treated as zero spend; 60-day window = minimum; non-blank Email column) and stopped to ask about them plus margin, instead of guessing. |
| Run | **PASS** | 1 × `run_audit` with the three paths, `contribution_margin` omitted after the user said they don't know it → report `20261114T064657Z-4887b8cc`. Artifacts in `agent_native/runs/20261114T064657Z-4887b8cc/`. |
| Report | **PASS** | 1 × `get_report`. Agent presented headline, per-campaign table with estimates + 95% CIs + labels + MDE80 + actions, inconclusive explanation, model/standing warnings, validation hold, assumed-margin disclosure, holdout recommendation. Every number checked against `result.json`; none invented. |

Tool calls, both runs: `validate_csv` ×3 → `run_audit` → `get_report`. No other tools were available or used.

## Headline numbers returned (identical in run 1, run 2, and the direct engine run)

Window 2024-01-01 → 2024-02-29 (60 days), Shopify order export, joint_revenue_ols_hc3, model estimated
(n=60, 14 parameters, residual df 46, R² 0.367, DW 2.28). Assumed margin 40% → break-even 2.50x.

- Total ad spend $13,115; platform-reported ROAS 4.77x ($62,537 claimed)
- **Store iROAS 1.22x, 95% CI [-0.02, 2.47]x, inconclusive, MDE80 1.77x**; incremental revenue $16,047

| Campaign | Est. iROAS | 95% CI | Label | MDE80 | Action (provisional; validation gate FAIL) |
|---|---:|---|---|---:|---|
| Google · Search - Brand | -0.00x | [-2.60, 2.60] | inconclusive | 3.70x | hold |
| Google · Search - Non-Brand | -0.82x | [-4.10, 2.45] | inconclusive | 4.65x | kill |
| Google · Shopping - US | -0.90x | [-3.36, 1.57] | inconclusive | 3.51x | kill |
| Meta · Lookalike - US | 2.20x | [0.75, 3.66] | positive | 2.07x | hold |
| Meta · Prospecting - US | 3.04x | [1.32, 4.77] | positive | 2.45x | hold |
| Meta · Retargeting - US | 2.34x | [1.13, 3.56] | positive | 1.73x | hold |

Warnings returned: model "Observational association: causal interpretation requires exogenous spend and a
valid model"; no data-quality warnings; standing limits (endogenous spend, carryover, missing days, HC3
scope, v2 S4/S5 calibration failures); legacy dashboard alerts (duplication 55%, ROAS inflated by 74%, no GSC).

## Gaps and findings

1. **Fixed — starter-prompt defect (run 1).** In run 1 the agent paraphrased the engine's legacy alert
   "Reported ROAS (4.77x) is inflated by 74% versus true incremental ROAS (1.22x)" as "Reported ROAS of
   4.77x is 74% above the estimated 1.22x" — arithmetically wrong (4.77 is ~290% above 1.22; 1.22 is 74%
   *below* 4.77). Fix (one edit to `STARTER_PROMPT.md`, "Honest limits"): do not re-express the tools'
   ratios or percentages; quote them as given. Also added, in the MCP layer only, a
   `legacy_health_alerts_note` and a "Legacy dashboard alerts (not campaign inference)" section in
   `report_markdown` explaining both metrics. Re-ran the full flow (run 2): the agent quoted all three
   alerts verbatim and wrote "The tool says: 'Estimated iROAS is 74% below platform-reported ROAS.'"
2. **Engine wording, not fixed (out of scope: engine files are read-only for this task).**
   `health_checks.py` says "More than 30% of reported conversions have no matching e-commerce order", but
   `deduplication.py` computes the rate from aggregate counts, not order matching. The MCP note states this;
   the engine message still overclaims and the agent (correctly) quotes it verbatim.
3. **Sample data shape.** Each repo ad sample has exactly one campaign row per day (60 rows, 3 campaigns,
   60 days), so ~2/3 of campaign-days are absent and treated as zero spend. The server's validation warning
   made the agent ask about it in both runs — good behaviour, but the stranger had to assert "the gaps are
   real". For a demo, a sample with every campaign on every day would avoid the question.
4. **Samples are 60 days**, the minimum; the prompt recommends 90. Validation flagged it; the agent
   explained the wide intervals accordingly.
5. **Margin question in non-interactive mode.** The prompt correctly makes the agent stop and ask for the
   margin before running; with `claude -p` this needed a second (resumed) turn. Not a defect.
6. **Agent asked about budget-setting/promotions (run 2)**, as the prompt's honest-limits section invites;
   the stranger didn't answer, and the agent then said so explicitly and kept the caution. Not a defect.
7. **`path` vs `content`.** With built-in tools removed, the agent could only pass `path`; the `content`
   mechanism was exercised by `smoke_test.py` (identical summaries by content and by path), not by the
   fresh session.
8. **Engine semantics surfaced as-is**: two campaigns are labeled *inconclusive* yet get a *kill* priority
   (CI includes zero but its upper bound is below 2.50x). The agent explained the distinction correctly in
   both runs. Shopify `Created at` timestamps with offsets are converted to UTC before day binning by
   `parse_date_column` (engine behaviour; not visible to the user; noted for later).

No step got stuck. Nothing outside `agent_native/` was modified.
