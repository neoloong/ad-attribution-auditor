# Build notes — agent-native MCP thin prototype (2026-11-13)

## What was built (all new files, all under `agent_native/`)

| File | Purpose |
|---|---|
| `mcp_server.py` | stdio MCP server: `initialize`, `ping`, `tools/list`, `tools/call`, notifications. Three tools. |
| `audit_service.py` | Glue from tool arguments to the existing engine; storage of runs; markdown rendering. No estimation logic. |
| `smoke_test.py` | Drives the server over real stdio JSON-RPC: valid samples (by content and by path), header/strict-numeric/daily-contract rejections, missing-Shopify-day warning, run + report, action-rule check, bad margin, bad id. |
| `STARTER_PROMPT.md` | Copy-paste prompt for a stranger's Claude. |
| `README.md` | Self-host setup, registration, tool I/O, artifacts, troubleshooting. |
| `.gitignore` | Ignores `runs/` (stored inputs may contain customer data). |
| `acceptance/` | Fresh-session acceptance: notes, transcript, raw logs, transcript renderer. |
| `runs/<id>/` | Run artifacts (inputs, request, result.json, report.md, daily_panel.csv). |

## Engine entry points reused (nothing reimplemented)

| Concern | File : function |
|---|---|
| CSV read + encoding detection, verbatim N/A text | `ad_audit/ingestion/loader.py : load_csv` |
| Exact headers, strict numeric rejection (2026-11-13 rules), Shopify daily contract | `ad_audit/ingestion/validators.py : validate_schema` (and its `value_errors` / `parse_numeric_column`); `InvalidInputError` |
| Required/optional headers reported to the agent | `ad_audit/ingestion/schemas.py : SCHEMAS` |
| Normalization per kind | `ad_audit/ingestion/normalizer.py : normalize_meta_ads, normalize_google_ads, normalize_shopify_orders, normalize_shopify_daily` |
| Missing interior Shopify days / daily-panel checks in `validate_csv` | `ad_audit/engine/aggregate_audit.py : _build_daily_merged` (called with an empty ad frame; its `data_quality_warnings`/`notes`) |
| End-to-end audit | `ad_audit/engine/aggregate_audit.py : run_aggregate_audit` (→ `campaign_regression.attach_campaign_spend`, `estimate_campaign_incrementality`) |
| Four-way label, delta 0.2x | `ad_audit/engine/models.py : classify_effect_interval` (store label; campaign labels come from `CampaignEstimate.effect_label`) |
| Break-even + margin validation | `scripts/gate1_pdf.py : margin_threshold` |
| Scale / kill / keep rule and reason text | `scripts/gate1_pdf.py : action_for_interval` |
| MDE80 | `scripts/run_v2_validation.py : mde_factor(residual_df)` × SE (same formula as the v2 calibration memo) |
| Validation hold semantics | `scripts/gate1_pdf.py : render_report` behaviour when `gate != "PASS"`; gate value read from `validation/v2-artifacts/sample-data.json` (written by `run_v2_validation.spec_gap(overall_gate='FAIL')`) |
| Legacy dashboard alerts | `ad_audit/engine/health_checks.py : run_health_checks` (same as `pages/3_Dashboard.py`) |

The engine is used as it is in the current working tree, including the uncommitted engine/ingestion
changes and untracked `campaign_regression.py` / `scripts/*` that were already present. Those files were
read and imported, never edited. `git status` outside `agent_native/` is identical to the starting snapshot.

Verified equivalence: the MCP report's store and campaign numbers equal a direct
`run_aggregate_audit` call on the same normalized inputs (checked during exploration and again in acceptance).

## Transport / library choice

**Zero-dependency stdio JSON-RPC MCP implementation** (newline-delimited JSON-RPC 2.0 on stdin/stdout, logs
on stderr), not the Python `mcp` SDK. Reasons: the repo venv has no `pip` module
(`.venv/bin/python -m pip` → "No module named pip"), so `pip install mcp` fails as specified; installing via
`uv` would have added ~15 packages (pydantic, starlette, anyio, httpx…) to a shared venv that the app and
tests depend on. The brief's fallback applies. The server negotiates protocol versions 2026-07-28,
2025-11-25, 2025-06-18, 2025-03-26 and 2024-11-05 (echoes the client's requested version if supported, else
offers the newest), declares the `tools` capability, returns `content` text + `structuredContent`, and
`isError` for failed runs. Claude Code 2.1.319 connected to it without issue.

Stdout is guarded: engine import and execution run under `redirect_stdout(sys.stderr)` so nothing can
corrupt the JSON-RPC stream.

## Input mechanism

Each dataset accepts `content` (CSV text — primary, because any agent that can read a file can send it,
including agents not on the server machine) or `path` (local path on the server machine — practical for
local self-host and large order exports). The acceptance session, with built-in tools removed, used `path`;
`content` is covered by `smoke_test.py`.

## Deviations from the brief, and why

1. **No `mcp` SDK** — see above (pip unavailable in venv; avoid mutating the shared venv).
2. **Action vocabulary.** The engine's rule (`action_for_interval`) returns `SCALE` / `KILL` / `KEEP`, and
   `KEEP` with reason "Inference unavailable; hold changes." for unavailable estimates. The report exposes
   both: `action` ∈ {`scale`, `kill`, `hold`, `null`} per the brief (KEEP → hold; unavailable → null, "NO
   ACTION"), plus the verbatim `engine_action` / `engine_action_reason`.
3. **Validation hold added.** The engine's own report renderer shows every action as "KEEP — hold" with a
   "Validation hold. Provisional priority: …" reason while the validation gate is FAIL (it is: v2
   calibration S1/S4/S5 FAIL). To stay consistent in meaning with the engine's output, every campaign also
   carries `report_action_under_validation_gate` / `report_action_reason`, and the markdown states the hold.
4. **Identification warnings.** The engine has no data-driven detector for demand-following (endogenous)
   spend or adstock/carryover; its per-run warnings are the model's "Observational association…" and serial-
   correlation warnings plus missing-day data-quality warnings. The report therefore lists those engine
   warnings and, separately, `identification_limitations`: the standing caveats copied from the engine's
   report methodology text (`render_report`) and the v2 calibration result. Nothing new is estimated.
5. **MDE80** is not part of `run_aggregate_audit` output; it is computed with the engine repo's own
   `mde_factor` from `scripts/run_v2_validation.py` × the engine's SE, at the model's residual df. Store-level
   MDE80 uses the same formula on the combined contrast's SE.
6. **Ad-file coverage note in `validate_csv`.** Listing calendar days with no ad row for any campaign, and the
   "<60 days" advisory, are bookkeeping facts computed in the MCP layer (labelled as such), because the engine
   only states that missing campaign-days are zero spend (`attach_campaign_spend`) and enforces ≥60 days at
   audit time. They do not change any estimate. The Email-column privacy note is likewise an MCP-layer note.
7. **At least one ad file** is required (the engine supports Meta-only or Google-only); the docs and prompt
   still ask for all three files.
8. **GSC brand-search input is not exposed** (brief specifies three datasets); the engine's "No Brand Search
   Data" info alert therefore always appears among legacy alerts.
9. **Legacy alerts note.** After acceptance run 1 (agent mis-paraphrased a percentage), the report gained a
   `legacy_health_alerts_note` explaining the duplication and inflation metrics; see ACCEPTANCE_NOTES.

## Known limits of the prototype

Synchronous runs; no auth, tenancy, quotas or deletion API; inputs stored in plain files under `runs/`;
local stdio only (no Streamable HTTP endpoint); single-user.
