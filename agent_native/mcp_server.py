#!/usr/bin/env python3
"""Ad Attribution Auditor — MCP server (stdio, zero external dependencies).

Speaks the Model Context Protocol over stdio: newline-delimited JSON-RPC 2.0
messages on stdin/stdout, logs on stderr.  Implements ``initialize``,
``notifications/initialized``, ``ping``, ``tools/list`` and ``tools/call``.

Run with the repo virtualenv (Python 3.12):

    /path/to/ad-attribution-auditor/.venv/bin/python /path/to/ad-attribution-auditor/agent_native/mcp_server.py

All analysis is delegated to ``agent_native/audit_service.py``, which only
calls the existing engine code paths.
"""
from __future__ import annotations

import json
import sys
import traceback
from pathlib import Path

if sys.version_info < (3, 10):
    sys.stderr.write("ad-attribution-auditor MCP: Python >= 3.10 required; use the repo's .venv/bin/python\n")
    sys.exit(1)

sys.path.insert(0, str(Path(__file__).resolve().parent))

SERVER_INFO = {"name": "ad-attribution-auditor", "version": "0.1.0-prototype"}
SUPPORTED_VERSIONS = ["2026-07-28", "2025-11-25", "2025-06-18", "2025-03-26", "2024-11-05"]
INSTRUCTIONS = (
    "Ad Attribution Auditor: incrementality audit from Meta Ads + Google Ads daily campaign CSVs and a "
    "Shopify orders (or daily totals) CSV. Workflow: validate_csv each file -> fix errors with the user -> "
    "run_audit -> get_report. Never invent numbers the tools did not return; 'inconclusive' is a valid result."
)

_SOURCE = {
    "content": {"type": "string",
                "description": "Full CSV text (UTF-8, one header row). Primary option: works for any agent."},
    "path": {"type": "string",
             "description": "Absolute path to the CSV on the machine running this server (local use only)."},
    "filename": {"type": "string", "description": "Optional display name used in error messages."},
}

TOOLS = [
    {
        "name": "validate_csv",
        "title": "Validate one CSV export",
        "description": (
            "Check one CSV against the engine's loader and validators before an audit. kind is one of "
            "meta_ads (headers: Day, Campaign name, Amount spent (USD), Purchases; optional Purchase conversion "
            "value, Purchase ROAS), google_ads (Day, Campaign, Cost, Conversions; optional Conv. value, "
            "Cost / conv.), shopify_orders (Name, Email, Created at, Total; optional Referring Site, Landing Site), "
            "shopify_daily (exactly date, orders, revenue, currency). Numbers must be plain decimals: no $, "
            "thousands separators, N/A, -- or blanks in required numeric columns. Supply the file as 'content' "
            "(CSV text) or 'path'. Returns ok, errors (file/column/row/value), warnings (e.g. missing interior "
            "days), and a summary (rows, date range, campaigns found) when valid."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {"kind": {"type": "string",
                                    "enum": ["meta_ads", "google_ads", "shopify_orders", "shopify_daily"]},
                           **_SOURCE},
            "required": ["kind"],
            "additionalProperties": False,
        },
        "annotations": {"readOnlyHint": True, "idempotentHint": True, "openWorldHint": False},
    },
    {
        "name": "run_audit",
        "title": "Run the incrementality audit",
        "description": (
            "Run the full audit (joint OLS of daily Shopify revenue on each campaign's daily spend + "
            "day-of-week + trend, HC3 95% intervals). Inputs: meta_ads and google_ads ({content} or {path}; at "
            "least one required, both expected), shopify ({kind: shopify_orders|shopify_daily, content|path}), "
            "optional contribution_margin in (0, 1] (if omitted the engine assumes 0.40 -> break-even 2.50x and "
            "actions are revenue-iROAS priorities, not profit calls). Runs synchronously; returns report_id and "
            "a one-line status. Then call get_report."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "meta_ads": {"type": "object", "properties": _SOURCE, "additionalProperties": False},
                "google_ads": {"type": "object", "properties": _SOURCE, "additionalProperties": False},
                "shopify": {"type": "object",
                            "properties": {"kind": {"type": "string", "enum": ["shopify_orders", "shopify_daily"],
                                                    "default": "shopify_orders"}, **_SOURCE},
                            "additionalProperties": False},
                "contribution_margin": {"type": "number", "exclusiveMinimum": 0, "maximum": 1,
                                        "description": "Contribution margin as a fraction, e.g. 0.35. "
                                                       "Omit only if the user does not know it."},
                "screening": {"type": "object", "description": "Optional intake Section B budget-behavior answers; "
                              "see audit_service / ad_audit.report.screening for fields. Omit if the user has not "
                              "answered the screening questions."},
            },
            "required": ["shopify"],
            "additionalProperties": False,
        },
        "annotations": {"readOnlyHint": False, "idempotentHint": False, "openWorldHint": False},
    },
    {
        "name": "get_report",
        "title": "Get a stored audit report",
        "description": (
            "Return the full structured result of a run_audit report_id: store-level iROAS with 95% CI, "
            "per-campaign estimate + 95% CI + label (positive / practically_zero / negative / inconclusive / "
            "unavailable) + MDE80 + provisional action priority (keep/kill/hold), the break-even threshold and "
            "margin disclosure, all warnings, and report_markdown with a holdout validation appendix. "
            "Use the appendix before increasing or cutting budgets."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {"report_id": {"type": "string"}},
            "required": ["report_id"],
            "additionalProperties": False,
        },
        "annotations": {"readOnlyHint": True, "idempotentHint": True, "openWorldHint": False},
    },
]


def log(*parts):
    print("[ad-attribution-auditor]", *parts, file=sys.stderr, flush=True)


_service = None


def service():
    global _service
    if _service is None:
        import contextlib
        with contextlib.redirect_stdout(sys.stderr):  # keep stdout pure JSON-RPC
            import audit_service
        _service = audit_service
    return _service


def call_tool(name: str, args: dict) -> dict:
    svc = service()
    if name == "validate_csv":
        result = svc.validate_csv(args.get("kind"), args.get("content"), args.get("path"), args.get("filename"))
        is_error = False  # a rejected file is a normal, structured answer
    elif name == "run_audit":
        result = svc.run_audit(args.get("meta_ads"), args.get("google_ads"), args.get("shopify"),
                               args.get("contribution_margin"), args.get("screening"))
        is_error = not result.get("ok", False)
    elif name == "get_report":
        result = svc.get_report(args.get("report_id"))
        is_error = not result.get("ok", False)
    else:
        raise KeyError(name)
    text = json.dumps(result, indent=1, allow_nan=False)
    return {"content": [{"type": "text", "text": text}], "structuredContent": result, "isError": is_error}


def handle(msg: dict):
    method, mid, params = msg.get("method"), msg.get("id"), msg.get("params") or {}
    if method == "initialize":
        requested = params.get("protocolVersion")
        version = requested if requested in SUPPORTED_VERSIONS else SUPPORTED_VERSIONS[0]
        return {"protocolVersion": version, "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": SERVER_INFO, "instructions": INSTRUCTIONS}
    if method == "ping":
        return {}
    if method == "tools/list":
        return {"tools": TOOLS}
    if method == "tools/call":
        name = params.get("name")
        if name not in {t["name"] for t in TOOLS}:
            raise JsonRpcError(-32602, f"Unknown tool: {name}")
        try:
            return call_tool(name, params.get("arguments") or {})
        except Exception as exc:  # report as a tool error, keep the server alive
            log(traceback.format_exc())
            return {"content": [{"type": "text", "text": f"Internal error in {name}: {type(exc).__name__}: {exc}"}],
                    "isError": True}
    if mid is None:
        return None  # notification (initialized, cancelled, ...): no reply
    raise JsonRpcError(-32601, f"Method not found: {method}")


class JsonRpcError(Exception):
    def __init__(self, code, message):
        super().__init__(message)
        self.code, self.message = code, message


def send(obj):
    sys.stdout.write(json.dumps(obj, allow_nan=False) + "\n")
    sys.stdout.flush()


def main():
    log("started; python", sys.version.split()[0], "-", sys.executable)
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError as exc:
            send({"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": f"Parse error: {exc}"}})
            continue
        batch = msg if isinstance(msg, list) else [msg]
        for m in batch:
            mid = m.get("id") if isinstance(m, dict) else None
            try:
                if not isinstance(m, dict) or "method" not in m:
                    if isinstance(m, dict) and ("result" in m or "error" in m):
                        continue  # response to a server->client request; we send none
                    raise JsonRpcError(-32600, "Invalid request")
                result = handle(m)
                if mid is not None:
                    send({"jsonrpc": "2.0", "id": mid, "result": result})
            except JsonRpcError as exc:
                if mid is not None:
                    send({"jsonrpc": "2.0", "id": mid, "error": {"code": exc.code, "message": exc.message}})
            except Exception as exc:
                log(traceback.format_exc())
                if mid is not None:
                    send({"jsonrpc": "2.0", "id": mid, "error": {"code": -32603, "message": str(exc)}})


if __name__ == "__main__":
    main()
