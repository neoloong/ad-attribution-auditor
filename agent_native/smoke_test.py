#!/usr/bin/env python3
"""Drive mcp_server.py over real stdio JSON-RPC and check the three tools.

    .venv/bin/python agent_native/smoke_test.py
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
DATA = ROOT / "data"


class Client:
    def __init__(self):
        self.p = subprocess.Popen([sys.executable, str(HERE / "mcp_server.py")], stdin=subprocess.PIPE,
                                  stdout=subprocess.PIPE, text=True, cwd="/tmp")
        self.n = 0

    def request(self, method, params=None):
        self.n += 1
        self.p.stdin.write(json.dumps({"jsonrpc": "2.0", "id": self.n, "method": method,
                                       "params": params or {}}) + "\n")
        self.p.stdin.flush()
        reply = json.loads(self.p.stdout.readline())
        assert reply["id"] == self.n, reply
        return reply

    def notify(self, method):
        self.p.stdin.write(json.dumps({"jsonrpc": "2.0", "method": method}) + "\n")
        self.p.stdin.flush()

    def tool(self, name, args):
        r = self.request("tools/call", {"name": name, "arguments": args})["result"]
        return json.loads(r["content"][0]["text"]), r["isError"]


def main():
    c = Client()
    init = c.request("initialize", {"protocolVersion": "2025-06-18", "capabilities": {},
                                    "clientInfo": {"name": "smoke", "version": "0"}})["result"]
    assert init["protocolVersion"] == "2025-06-18"
    c.notify("notifications/initialized")
    names = [t["name"] for t in c.request("tools/list")["result"]["tools"]]
    assert names == ["validate_csv", "run_audit", "get_report"], names

    # 1. valid files, by content and by path
    for kind, f in (("meta_ads", "sample_meta_ads.csv"), ("google_ads", "sample_google_ads.csv"),
                    ("shopify_orders", "sample_shopify_orders.csv")):
        res, _ = c.tool("validate_csv", {"kind": kind, "content": (DATA / f).read_text(), "filename": f})
        assert res["ok"], res
        res2, _ = c.tool("validate_csv", {"kind": kind, "path": str(DATA / f)})
        assert res2["ok"] and res2["summary"] == res["summary"]
        print(f"validate {kind}: ok, {res['summary']['rows']} rows, {res['summary']['date_range']}")

    # 2. rejections: wrong header, strict numeric, interior Shopify gap, daily contract
    bad_header = (DATA / "sample_meta_ads.csv").read_text().replace("Amount spent (USD)", "Spend", 1)
    res, _ = c.tool("validate_csv", {"kind": "meta_ads", "content": bad_header})
    assert not res["ok"] and "Amount spent (USD)" in res["errors"][0], res
    bad_num = "Day,Campaign,Cost,Conversions\n2024-01-01,A,\"$1,200\",3\n2024-01-02,A,N/A,2\n"
    res, _ = c.tool("validate_csv", {"kind": "google_ads", "content": bad_num, "filename": "g.csv"})
    assert not res["ok"] and len(res["errors"]) == 2 and "'$1,200'" in res["errors"][0], res
    lines = (DATA / "sample_shopify_orders.csv").read_text().splitlines()
    gap = "\n".join([lines[0]] + [l for l in lines[1:] if "2024-01-15" not in l]) + "\n"
    res, _ = c.tool("validate_csv", {"kind": "shopify_orders", "content": gap})
    assert res["ok"] and any("Missing Shopify days" in w and "2024-01-15" in w for w in res["warnings"]), res
    daily = "date,orders,revenue,currency\n2024-01-01,3,300,USD\n2024-01-03,0,5,USD\n2024-01-03,1,1.5,EUR\n"
    res, _ = c.tool("validate_csv", {"kind": "shopify_daily", "content": daily})
    assert not res["ok"] and any("duplicate date" in e for e in res["errors"]), res
    print("rejections: ok (", len(res["errors"]), "daily-contract errors )")

    # 3. run + report, default margin
    run, err = c.tool("run_audit", {"meta_ads": {"path": str(DATA / "sample_meta_ads.csv")},
                                    "google_ads": {"path": str(DATA / "sample_google_ads.csv")},
                                    "shopify": {"kind": "shopify_orders",
                                                "path": str(DATA / "sample_shopify_orders.csv")}})
    assert run["ok"] and not err, run
    print(run["status"])
    rep, err = c.tool("get_report", {"report_id": run["report_id"]})
    assert rep["ok"] and not err
    r = rep["report"]
    assert r["decision_rule"]["break_even_iroas"] == 2.5 and r["decision_rule"]["margin_source"] == "assumed"
    for camp in r["campaigns"]:
        lo, hi = camp["confidence_interval"]
        be = 2.5
        assert camp["action"] == ("keep" if lo > be else "kill" if hi < be else "hold"), camp
        assert camp["mde80"] > 0
    assert (Path(rep["artifacts_dir"]) / "report.md").is_file()

    # 4. margin validation and bad id
    run2, err = c.tool("run_audit", {"meta_ads": {"path": str(DATA / "sample_meta_ads.csv")},
                                     "shopify": {"path": str(DATA / "sample_shopify_orders.csv")},
                                     "contribution_margin": 1.5})
    assert err and not run2["ok"], run2
    bad, err = c.tool("get_report", {"report_id": "../../etc"})
    assert err and not bad["ok"]
    c.p.stdin.close()
    c.p.wait(timeout=10)
    print("SMOKE TEST PASSED")
    print(rep["report_markdown"])


if __name__ == "__main__":
    main()
