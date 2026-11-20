#!/usr/bin/env python3
"""Render claude -p stream-json logs (raw/runN/turnK.jsonl) into a readable transcript."""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def render(run_dir: Path) -> tuple[str, list[str]]:
    out, tools = [], []
    for turn in sorted(run_dir.glob("turn*.jsonl")):
        prompt = (run_dir / (turn.stem + ".txt")).read_text()
        out += [f"\n{'#' * 78}\n# {run_dir.name} / {turn.stem}\n{'#' * 78}\n", "=== USER ===", prompt.rstrip(), ""]
        for line in turn.read_text().splitlines():
            ev = json.loads(line)
            if ev.get("type") == "system" and ev.get("subtype") == "init":
                out.append(f"[session init: cwd={ev.get('cwd')} model={ev.get('model')} tools={ev.get('tools')} "
                           f"mcp_servers={ev.get('mcp_servers')}]")
            elif ev.get("type") == "assistant":
                for block in ev["message"].get("content", []):
                    if block.get("type") == "text":
                        out += ["=== ASSISTANT ===", block["text"], ""]
                    elif block.get("type") == "tool_use":
                        tools.append(block["name"])
                        out += [f"=== TOOL CALL: {block['name']} ===", json.dumps(block["input"], indent=1), ""]
            elif ev.get("type") == "user":
                content = ev["message"].get("content", [])
                for block in content if isinstance(content, list) else []:
                    if block.get("type") == "tool_result":
                        body = block.get("content")
                        if isinstance(body, list):
                            body = "\n".join(b.get("text", "") for b in body if isinstance(b, dict))
                        out += [f"=== TOOL RESULT{' (error)' if block.get('is_error') else ''} ===", str(body), ""]
            elif ev.get("type") == "result":
                out.append(f"[turn end: subtype={ev.get('subtype')} turns={ev.get('num_turns')} "
                           f"duration_ms={ev.get('duration_ms')} cost_usd={ev.get('total_cost_usd')}]")
    return "\n".join(out), tools


if __name__ == "__main__":
    parts = ["Ad Attribution Auditor — agent-native acceptance transcripts",
             "Generated from agent_native/acceptance/raw/run*/turn*.jsonl (claude -p --output-format stream-json).",
             "run2 is the acceptance-of-record (after one starter-prompt fix); run1 is kept as evidence of the gap found."]
    for run in sorted(p for p in (HERE / "raw").iterdir() if p.is_dir()):
        text, tools = render(run)
        parts += [text, f"\n[{run.name} tool calls: {tools}]"]
        print(run.name, tools, file=sys.stderr)
    (HERE / "acceptance-transcript.txt").write_text("\n".join(parts) + "\n")
