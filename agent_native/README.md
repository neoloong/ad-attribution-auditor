# Ad Attribution Auditor — agent-native MCP server (self-host prototype)

> **Local / self-host prototype. There is no hosted endpoint yet.** The server runs on your own machine
> over stdio and is started by your Claude client. Nothing is uploaded anywhere; inputs and results are
> written to `agent_native/runs/` on the same machine.

Your own Claude (Claude Code or Claude Desktop) connects to this server over MCP and runs the whole audit in
conversation: validate the three CSV exports, run the audit, and read back a report. The analysis is the
existing engine in `ad_audit/` (the same code paths the Streamlit app and `scripts/` use); this directory
adds only an MCP adapter. To hand the workflow to a user, give them [`STARTER_PROMPT.md`](STARTER_PROMPT.md).

## Prerequisites

- This repository checked out, e.g. at `<INSTALL_PATH>` = `/Users/chao/dev/ad-attribution-auditor`.
- Its virtualenv at `<INSTALL_PATH>/.venv` with **Python 3.12** and the repo's `requirements.txt` installed
  (pandas, numpy, scipy, chardet, python-dateutil). Check:
  `<INSTALL_PATH>/.venv/bin/python -c "import pandas, scipy, chardet; print('ok')"`.
- No extra packages: the MCP layer is a zero-dependency stdio JSON-RPC implementation.
- Do **not** use a system `python3` (on the reference Mac it is 3.9 and lacks the dependencies).

## Start the server

Your MCP client starts it for you. To run it by hand (it then waits for JSON-RPC on stdin; Ctrl-C to quit):

```sh
<INSTALL_PATH>/.venv/bin/python <INSTALL_PATH>/agent_native/mcp_server.py
```

Self-test over real stdio (validates the repo samples, checks rejections, runs one audit, prints the report):

```sh
<INSTALL_PATH>/.venv/bin/python <INSTALL_PATH>/agent_native/smoke_test.py
```

## Register it

**Claude Code**

```sh
claude mcp add --scope user ad-attribution-auditor -- \
  <INSTALL_PATH>/.venv/bin/python <INSTALL_PATH>/agent_native/mcp_server.py
claude mcp list        # ad-attribution-auditor should be listed as connected
```

Use `--scope local` (default) to register it for one project only. For a one-off session without
changing settings, use a config file and `claude --mcp-config ./auditor-mcp.json --strict-mcp-config`:

```json
{"mcpServers": {"ad-attribution-auditor": {"type": "stdio",
  "command": "<INSTALL_PATH>/.venv/bin/python",
  "args": ["<INSTALL_PATH>/agent_native/mcp_server.py"]}}}
```

**Claude Desktop** — Settings → Developer → Edit Config
(`~/Library/Application Support/Claude/claude_desktop_config.json`; Windows:
`%APPDATA%\Claude\claude_desktop_config.json`), then fully quit and restart Claude Desktop:

```json
{
  "mcpServers": {
    "ad-attribution-auditor": {
      "command": "<INSTALL_PATH>/.venv/bin/python",
      "args": ["<INSTALL_PATH>/agent_native/mcp_server.py"]
    }
  }
}
```

## Tools

Every dataset can be supplied two ways: `content` (the full CSV text — the **primary** mechanism, because any
agent that can read a file can supply it, including agents not running on the server machine) or `path`
(absolute path on the machine running the server — convenient locally and for large order exports). Exactly
one of the two per file. Optional `filename` sets the name used in error messages.

### `validate_csv`

Input: `kind` (`meta_ads` | `google_ads` | `shopify_orders` | `shopify_daily`) + `content` or `path`.

Runs `load_csv` → `validate_schema` (exact headers + strict numeric/daily-contract checks) → the kind's
normalizer, and for Shopify files the engine's missing-day check. Output:

```json
{"ok": true, "kind": "meta_ads", "file": "...", "errors": [], "warnings": ["..."],
 "required_headers": [...], "optional_headers": [...],
 "summary": {"rows": 60, "date_range": {"start": "...", "end": "...", "calendar_days": 60, "days_with_rows": 60},
             "campaigns_found": [{"campaign_name": "...", "rows": 16, "total_spend": 2516.41, ...}],
             "total_spend": 5836.0}}
```

Errors are the engine's own messages, e.g. `g.csv: column 'Cost', data row 1 (Day='2024-01-01',
Campaign='A'): value '$1,200' is not a valid number`, or `missing required column(s) ['Amount spent (USD)']`.
Missing interior Shopify days come back as the engine warning `Missing Shopify days inside observed date
range (N): ...` (never zero-filled). For ad files, calendar days with no row for any campaign are listed,
since the engine treats a missing campaign-day as zero spend.

Required headers (from `ad_audit/ingestion/schemas.py`):

| kind | required | optional |
|---|---|---|
| `meta_ads` | `Day`, `Campaign name`, `Amount spent (USD)`, `Purchases` | `Purchase conversion value`, `Purchase ROAS` |
| `google_ads` | `Day`, `Campaign`, `Cost`, `Conversions` | `Conv. value`, `Cost / conv.` |
| `shopify_orders` | `Name`, `Email`, `Created at`, `Total` | `Referring Site`, `Landing Site` |
| `shopify_daily` | exactly `date`, `orders`, `revenue`, `currency` (no other columns) | — |

### `run_audit`

Input: `meta_ads` `{content|path}`, `google_ads` `{content|path}` (at least one; both expected),
`shopify` `{kind: shopify_orders|shopify_daily, content|path}`, optional `contribution_margin` in (0, 1].

Re-validates every file, then calls `run_aggregate_audit` synchronously and stores the result. Output:
`{"ok": true, "report_id": "20261114T064312Z-4887b8cc", "status": "Audit complete: 6 campaign(s), ..."}`.
On bad inputs: `{"ok": false, "errors": [...]}` and nothing is run.

### `get_report`

Input: `report_id`. Output: `{"ok": true, "report": {...}, "report_markdown": "...", "artifacts_dir": "..."}`.
`report` contains:

- `store` — `asdict(IncrementalROASResult)`: spend, platform ROAS, `true_incremental_roas`, 95%
  `confidence_interval`, `standard_error`, `estimation_method`, plus `effect_label` and `mde80`.
- `campaigns[]` — `asdict(CampaignEstimate)` (estimate, CI, SE, `effect_label`, `status`, `warnings`) plus
  `mde80`, provisional `action` (`keep` | `kill` | `hold`), `action_display`, and the visible priority and
  its reason in the existing `engine_action` / `engine_action_reason` fields. A validation hold also reports
  `report_action_under_validation_gate` (`hold`) and `report_action_reason`.
- `decision_rule` — margin, `margin_source` (`assumed`|`customer`), `break_even_iroas` = 1/margin, the rule
  text, provisional-priority notice, and label rule (practical-zero band ±0.2x).
- `warnings` — `data_quality`, `data_quality_notes`, `model`, per-`campaign`, `input_files`, and the
  standing `identification_limitations` (endogenous spend, carryover, missing days).
- `model_diagnostics`, `legacy_health_alerts` (dashboard heuristics; not campaign inference), `dataset`,
  `inputs` (file name + SHA-256), `engine`.

`report_markdown` renders the same numbers as plain text and includes the holdout design appendix.
Opening an older report uses the current wording and the saved estimates.

## Run artifacts

`agent_native/runs/<report_id>/`:

- `inputs/<kind>.csv` — the exact bytes received
- `request.json` — margin and Shopify kind requested
- `result.json` — the structured report returned by `get_report`
- `report.md` — the rendered report
- `daily_panel.csv` — the engine's merged daily panel (`AuditResult.daily_df`)

Inputs may contain customer data; `runs/` is git-ignored (`agent_native/.gitignore`). Delete runs when done.

## Troubleshooting

- **Wrong Python** — `ModuleNotFoundError: pandas` or a 3.9 interpreter in the client log: the registered
  command must be `<INSTALL_PATH>/.venv/bin/python`, an absolute path. The server exits with a message on
  Python < 3.10. The server logs its interpreter to stderr on start.
- **Server not listed / not connected** — run `claude mcp list`; run the start command above by hand and
  confirm it prints `[ad-attribution-auditor] started` on stderr; check that both paths are absolute and
  exist; in Claude Desktop, check Settings → Developer for the server's log and fully restart the app after
  editing the config. `claude mcp get ad-attribution-auditor` shows the registered command.
- **Missing headers** — headers are exact; `validate_csv` names the missing ones and lists what it found.
  Common causes: Meta export in a non-USD currency (`Amount spent (EUR)`), Google's title rows above the
  header, Shopify daily files with extra columns.
- **Rejected numbers** — `$`, `1,200`, `N/A`, `--`, blanks in required number columns are rejected by design
  (strict numeric rule). Re-export as plain numbers.
- **Campaign results "unavailable"** — fewer than 60 days, missing Shopify days, gaps, or collinear spend;
  the reason is in each campaign's `warnings`.
- **Path not found** — `path` is resolved on the machine running the server; use `content` from remote agents.
