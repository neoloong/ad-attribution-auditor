"""Engine glue for the agent-native MCP prototype.

This module contains NO estimation logic. It uses the existing audit code
paths for estimates, evidence labels and underlying actions:

* ``ad_audit.ingestion.loader.load_csv``                 - CSV bytes -> DataFrame
* ``ad_audit.ingestion.validators.validate_schema``      - headers + strict values
* ``ad_audit.ingestion.normalizer.normalize_*``          - per-kind normalizers
* ``ad_audit.engine.aggregate_audit._build_daily_merged`` - missing Shopify day check
* ``ad_audit.engine.aggregate_audit.run_aggregate_audit`` - end-to-end audit
* ``ad_audit.engine.models.classify_effect_interval``    - four-way evidence label
* ``ad_audit.engine.health_checks.run_health_checks``    - legacy dashboard alerts
* ``scripts.gate1_pdf.margin_threshold`` / ``provisional_action_for_interval`` - break-even + report priorities
* ``scripts.run_v2_validation.mde_factor``               - MDE80 factor (x SE)

This service handles bookkeeping, intake screening for presentation, and text rendering.
"""
from __future__ import annotations

import contextlib
import datetime as _dt
import hashlib
import io
import json
import math
import re
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from ad_audit.engine.aggregate_audit import _build_daily_merged, run_aggregate_audit  # noqa: E402
from ad_audit.engine.health_checks import run_health_checks  # noqa: E402
from ad_audit.engine.models import AuditConfig, AuditMode, classify_effect_interval  # noqa: E402
from ad_audit.ingestion.loader import load_csv  # noqa: E402
from ad_audit.ingestion.normalizer import (  # noqa: E402
    normalize_google_ads,
    normalize_meta_ads,
    normalize_shopify_daily,
    normalize_shopify_orders,
)
from ad_audit.ingestion.schemas import SCHEMAS  # noqa: E402
from ad_audit.ingestion.validators import InvalidInputError, validate_schema  # noqa: E402
from ad_audit.report import screening as budget_screening  # noqa: E402
from ad_audit.report.holdout import ACTION_NOTICE, appendix_markdown  # noqa: E402
from scripts.gate1_pdf import (  # noqa: E402
    ACTION_RULE,
    label_action_note,
    margin_threshold,
    provisional_action_for_interval,
)
from scripts.run_v2_validation import mde_factor  # noqa: E402

RUNS_DIR = Path(__file__).resolve().parent / "runs"
KINDS = ("meta_ads", "google_ads", "shopify_orders", "shopify_daily")
NORMALIZERS = {
    "meta_ads": normalize_meta_ads,
    "google_ads": normalize_google_ads,
    "shopify_orders": normalize_shopify_orders,
    "shopify_daily": normalize_shopify_daily,
}
DELTA = 0.2  # classify_effect_interval default practical-equivalence region (+/-0.2x)
RUN_ID_RE = re.compile(r"^[0-9]{8}T[0-9]{6}Z-[0-9a-f]{8}$")

# Verbatim methodology limitations from scripts/gate1_pdf.py:render_report
# (section "Causal and financial limitations" and "Uncertainty").  The engine
# has no data-driven detector for endogenous spend or adstock; these are its
# standing identification caveats and are reported as such.
ENGINE_LIMITATIONS = [
    "HC3 does not correct serial correlation or endogenous spend.",
    "Promotions, omitted channels, nonlinear seasonality, carryover, saturation and interactions can bias estimates.",
    "Missing campaign-date rows are treated as zero spend; missing interior Shopify days disable campaign inference.",
    "Intervals are marginal 95% HC3 intervals, conditional on observed spend, and do not establish real-world causality.",
    "Validation v2 calibration found bias with endogenous (demand-following) spend and with carryover/adstock "
    "(scenarios S4 and S5 FAIL in validation/v2-calibration-2026-11-09.md); validate material budget changes "
    "with a controlled holdout.",
]


class InputProblem(Exception):
    """Raised when a supplied dataset cannot even be read."""


# ---------------------------------------------------------------- helpers

def _clean(value: Any) -> Any:
    """Make engine output JSON-safe (NaN/inf -> None, numpy -> python)."""
    if isinstance(value, dict):
        return {str(k): _clean(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_clean(v) for v in value]
    if isinstance(value, (np.bool_,)):
        return bool(value)
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (float, np.floating)):
        v = float(value)
        return v if math.isfinite(v) else None
    if isinstance(value, (pd.Timestamp, _dt.date)):
        return value.strftime("%Y-%m-%d")
    if hasattr(value, "value") and value.__class__.__module__.startswith("ad_audit"):
        return value.value  # enums
    return value


def _read_source(content: str | None, path: str | None) -> tuple[bytes, str | None]:
    if content is not None and path:
        raise InputProblem("Supply either 'content' or 'path', not both.")
    if content is not None:
        if not content.strip():
            raise InputProblem("'content' is empty.")
        return content.encode("utf-8"), None
    if path:
        p = Path(path).expanduser()
        if not p.is_file():
            raise InputProblem(f"File not found on the server machine: {p}")
        return p.read_bytes(), p.name
    raise InputProblem("Supply the CSV as 'content' (text) or 'path' (file on the server machine).")


def _load(kind: str, raw: bytes, source: str):
    """Run the engine loader, header/value validation and normalizer."""
    errors: list[str] = []
    warnings: list[str] = []
    try:
        df = load_csv(io.BytesIO(raw), source_name=source)
    except InvalidInputError as exc:  # e.g. row field count != header (unquoted 1,234)
        return None, None, list(exc.errors), warnings
    except Exception as exc:  # pandas parser errors, empty file, encoding
        return None, None, [f"{source}: could not be read as CSV ({type(exc).__name__}: {exc})"], warnings

    result = validate_schema(df, kind, source_name=source)
    if result.missing_required:
        # Same wording as validators.raise_if_invalid
        errors.append(f"{source}: missing required column(s) {result.missing_required}")
        errors.append(
            f"{source}: required headers for {kind} are exactly {sorted(SCHEMAS[kind].required)} "
            f"(found {list(df.columns)})"
        )
    errors.extend(result.errors)
    warnings.extend(result.warnings)
    if result.missing_optional:
        warnings.append(f"{source}: optional column(s) not present: {result.missing_optional}")
    if result.extra_columns and not SCHEMAS[kind].exact_columns:
        warnings.append(f"{source}: extra column(s) ignored by the engine: {result.extra_columns}")
    if errors:
        return df, None, errors, warnings

    try:
        normalized = NORMALIZERS[kind](df, source_name=source)
    except InvalidInputError as exc:
        return df, None, list(exc.errors), warnings
    except Exception as exc:  # e.g. unparseable dates
        return df, None, [f"{source}: rejected during normalization ({type(exc).__name__}: {exc})"], warnings
    return df, normalized, errors, warnings


def _shopify_coverage_warnings(shop: pd.DataFrame) -> tuple[list[str], list[str]]:
    """Engine's own missing-Shopify-day check, run with no ad rows."""
    empty_ads = pd.DataFrame({
        "date": pd.Series(dtype="datetime64[ns]"), "spend": pd.Series(dtype=float),
        "reported_conversions": pd.Series(dtype=float), "reported_revenue": pd.Series(dtype=float),
        "platform": pd.Series(dtype=str), "campaign_name": pd.Series(dtype=str),
    })
    daily = _build_daily_merged(empty_ads, shop, None)
    return list(daily.attrs.get("data_quality_warnings", [])), list(daily.attrs.get("data_quality_notes", []))


def _summary(kind: str, raw_df: pd.DataFrame, norm: pd.DataFrame) -> tuple[dict, list[str]]:
    notes: list[str] = []
    dates = pd.DatetimeIndex(norm["date"])
    start, end = dates.min(), dates.max()
    span = int((end - start).days) + 1
    summary: dict[str, Any] = {
        "rows": int(len(raw_df)),
        "date_range": {"start": start.strftime("%Y-%m-%d"), "end": end.strftime("%Y-%m-%d"),
                       "calendar_days": span, "days_with_rows": int(dates.normalize().nunique())},
    }
    if kind in ("meta_ads", "google_ads"):
        camp = (norm.groupby("campaign_name")
                .agg(rows=("spend", "size"), spend=("spend", "sum"),
                     first_day=("date", "min"), last_day=("date", "max"))
                .reset_index())
        summary["campaigns_found"] = [
            {"campaign_name": r.campaign_name, "rows": int(r.rows), "total_spend": round(float(r.spend), 2),
             "first_day": r.first_day.strftime("%Y-%m-%d"), "last_day": r.last_day.strftime("%Y-%m-%d")}
            for r in camp.itertuples()
        ]
        summary["total_spend"] = round(float(norm["spend"].sum()), 2)
        expected = pd.date_range(start, end, freq="D")
        no_rows = expected.difference(dates.normalize().unique())
        if len(no_rows):
            notes.append(
                f"{len(no_rows)} calendar day(s) inside this file's date range have no row for any campaign: "
                + ", ".join(d.strftime("%Y-%m-%d") for d in no_rows)
                + ". The engine treats a missing campaign-date row as ZERO spend "
                  "(campaign_regression.attach_campaign_spend); confirm these were genuine zero-spend days "
                  "or re-export the complete range."
            )
        notes.append("Campaign-days with no row are treated by the engine as zero spend for that campaign; "
                     "export every day of the window, including days a campaign was paused.")
    else:
        if kind == "shopify_orders":
            summary["orders"] = int(len(norm))
            summary["revenue_total"] = round(float(norm["revenue"].sum()), 2)
            if "Email" in raw_df.columns:
                filled = int(raw_df["Email"].astype(str).str.strip().replace("nan", "").ne("").sum())
                if filled:
                    notes.append(
                        f"Email column has {filled} non-blank value(s). The engine only hashes it; "
                        "keep the column but blank it before sharing to avoid passing customer personal data."
                    )
        else:
            summary["orders"] = int(norm["orders"].sum())
            summary["revenue_total"] = round(float(norm["revenue"].sum()), 2)
            summary["currency"] = norm.attrs.get("currency")
        dq_warnings, dq_notes = _shopify_coverage_warnings(norm)
        summary["engine_data_quality_warnings"] = dq_warnings
        notes.extend(dq_notes)
    if span < 60:
        notes.append(f"Only {span} calendar days; the engine requires at least 60 complete daily "
                     "observations for campaign inference (90 recommended).")
    return summary, notes


# ---------------------------------------------------------------- tool 1

def validate_csv(kind: str, content: str | None = None, path: str | None = None,
                 filename: str | None = None) -> dict:
    if kind not in KINDS:
        return {"ok": False, "kind": kind, "errors": [f"Unknown kind {kind!r}; use one of {list(KINDS)}"],
                "warnings": []}
    try:
        raw, name = _read_source(content, path)
    except InputProblem as exc:
        return {"ok": False, "kind": kind, "errors": [str(exc)], "warnings": []}
    source = filename or name or f"<{kind} CSV>"
    raw_df, norm, errors, warnings = _load(kind, raw, source)
    out: dict[str, Any] = {"ok": not errors and norm is not None, "kind": kind, "file": source,
                           "errors": errors, "warnings": warnings,
                           "required_headers": sorted(SCHEMAS[kind].required),
                           "optional_headers": sorted(SCHEMAS[kind].optional)}
    if out["ok"]:
        summary, notes = _summary(kind, raw_df, norm)
        out["summary"] = summary
        out["warnings"].extend(summary.pop("engine_data_quality_warnings", []))
        out["warnings"].extend(notes)
    return _clean(out)


# ---------------------------------------------------------------- tool 2

def _mde80(se: float | None, residual_df: int | None) -> float | None:
    if se is None or residual_df is None or not math.isfinite(se):
        return None
    return float(se * mde_factor(residual_df))


def _validation_gate() -> str:
    """Gate the engine's own report renderer uses (scripts/run_v2_validation.spec_gap)."""
    try:
        sample = json.loads((REPO_ROOT / "validation/v2-artifacts/sample-data.json").read_text())
        return str(sample.get("gate", "FAIL"))
    except Exception:
        return "FAIL"


def _action(ci, threshold: float, gate: str) -> dict:
    action, reason = provisional_action_for_interval(ci, threshold)
    out = {"action": action, "action_display": f"{action} (provisional)",
           "engine_action": action, "engine_action_reason": reason}
    if gate != "PASS":
        out["report_action_under_validation_gate"] = "hold"
        out["report_action_reason"] = f"Validation hold. Provisional priority: {action}. {reason}"
    return out


def _apply_report_wording(report: dict) -> None:
    rule = report["decision_rule"]
    margin = rule["contribution_margin"]
    threshold = rule["break_even_iroas"]
    margin_note = "Assumed" if rule["margin_source"] == "assumed" else "Customer-supplied"
    rule["rule"] = (f"{margin_note} contribution margin: {margin:.0%}. "
                    f"Break-even iROAS = 1/margin = {threshold:.2f}x. {ACTION_RULE}")
    rule["action_notice"] = ACTION_NOTICE
    rule["profit_calls"] = False
    gate = report["engine"]["validation_gate"]
    level = (report.get("screening") or {}).get("risk_level")
    for campaign in report["campaigns"]:
        campaign.update(_action(campaign["confidence_interval"], threshold, gate))
        if level == "high":
            action = budget_screening.presentation_action(campaign["action"], level)
            campaign["action_display"] = f"{action} (provisional)"


def run_audit(meta_ads: dict | None = None, google_ads: dict | None = None, shopify: dict | None = None,
              contribution_margin: float | None = None, screening: dict | None = None) -> dict:
    datasets = {"meta_ads": meta_ads, "google_ads": google_ads}
    errors: list[str] = []
    if not (meta_ads or google_ads):
        errors.append("Supply at least one ad platform file (meta_ads and/or google_ads); three files expected.")
    if not shopify:
        errors.append("Supply the Shopify file as 'shopify' with kind 'shopify_orders' or 'shopify_daily'.")
    shop_kind = (shopify or {}).get("kind", "shopify_orders")
    if shopify and shop_kind not in ("shopify_orders", "shopify_daily"):
        errors.append(f"shopify.kind must be 'shopify_orders' or 'shopify_daily', got {shop_kind!r}")
    try:
        margin, threshold = margin_threshold(contribution_margin)
    except (ValueError, TypeError) as exc:
        errors.append(f"contribution_margin: {exc}")
        margin = threshold = None
    try:
        assessment = (budget_screening.not_screened() if screening is None
                      else budget_screening.assess_screening(screening))
    except ValueError as exc:
        errors.append(f"screening: {exc}")
    if errors:
        return {"ok": False, "status": "rejected: " + errors[0], "errors": errors}

    loaded: dict[str, tuple[bytes, pd.DataFrame, str]] = {}
    file_warnings: list[str] = []
    for kind, spec in list(datasets.items()) + [(shop_kind, shopify)]:
        if not spec:
            continue
        try:
            raw, name = _read_source(spec.get("content"), spec.get("path"))
        except InputProblem as exc:
            errors.append(f"{kind}: {exc}")
            continue
        source = spec.get("filename") or name or f"<{kind} CSV>"
        raw_df, norm, errs, warns = _load(kind, raw, source)
        errors.extend(errs)
        file_warnings.extend(warns)
        if norm is not None:
            loaded[kind] = (raw, norm, source)
    if errors:
        return {"ok": False, "status": f"rejected: {len(errors)} input error(s); fix and re-run validate_csv",
                "errors": errors, "warnings": file_warnings}

    ads = pd.concat([loaded[k][1] for k in ("meta_ads", "google_ads") if k in loaded], ignore_index=True)
    shop = loaded[shop_kind][1]
    # Engine prints nothing to stdout today, but stdout is the MCP channel: guard it.
    with contextlib.redirect_stdout(sys.stderr):
        try:
            result = run_aggregate_audit(ads, shop, None, AuditConfig(mode=AuditMode.AGGREGATE))
        except ValueError as exc:
            return {"ok": False, "status": f"rejected by engine: {exc}", "errors": [str(exc)]}
        alerts = run_health_checks(result)

    gate = _validation_gate()
    model = result.extras.get("campaign_model", {})
    residual_df = model.get("residual_df")
    store = asdict(result.incremental_roas)
    store["effect_label"] = classify_effect_interval(store["confidence_interval"])
    store["mde80"] = _mde80(store["standard_error"], residual_df) if store["confidence_interval"] else None
    if store["estimation_method"] != "joint_revenue_ols_hc3":
        store["note"] = ("Joint campaign model unavailable; this is the legacy store heuristic, "
                         "explicitly uncalibrated (aggregate_audit.run_aggregate_audit).")

    campaigns = []
    for c in result.campaign_results:
        row = asdict(c)
        row["mde80"] = _mde80(c.standard_error, residual_df) if c.confidence_interval else None
        campaigns.append(row)

    daily = result.daily_df
    assumed = contribution_margin is None
    created = _dt.datetime.now(_dt.timezone.utc)
    digest = hashlib.sha256(b"".join(v[0] for v in loaded.values()) + repr(contribution_margin).encode())
    if assessment["provided"]:
        digest.update(json.dumps(assessment["answers"], sort_keys=True).encode())
    run_id = created.strftime("%Y%m%dT%H%M%SZ") + "-" + digest.hexdigest()[:8]

    warnings = {
        "data_quality": list(result.extras.get("data_quality_warnings", [])),
        "data_quality_notes": list(result.extras.get("data_quality_notes", [])),
        "model": list(model.get("warnings", [])),
        "campaign": {c["campaign_name"]: c["warnings"] for c in campaigns if c["warnings"]},
        "input_files": file_warnings,
        "identification_limitations": ENGINE_LIMITATIONS,
    }
    report = {
        "report_id": run_id,
        "created_utc": created.isoformat(),
        "engine": {"pipeline": "ad_audit.engine.aggregate_audit.run_aggregate_audit",
                   "method": model.get("method", store["estimation_method"]),
                   "model_status": model.get("status"),
                   "validation_gate": gate},
        "inputs": {k: {"file": v[2], "sha256": hashlib.sha256(v[0]).hexdigest()} for k, v in loaded.items()},
        "dataset": {"start": daily["date"].min(), "end": daily["date"].max(), "days": int(len(daily)),
                    "shopify_granularity": result.extras.get("shopify_granularity")},
        "decision_rule": {"contribution_margin": margin, "margin_source": "assumed" if assumed else "customer",
                          "break_even_iroas": threshold,
                          "label_rule": model.get("effect_label_rule",
                                                  "Practical equivalence first (CI inside +/-0.2x), then sign, "
                                                  "else inconclusive"),
                          "practical_zero_delta": DELTA},
        "store": store,
        "campaigns": campaigns,
        "screening": assessment,
        "warnings": warnings,
        "model_diagnostics": {k: v for k, v in model.items() if k != "campaigns"},
        "legacy_health_alerts": [asdict(a) for a in alerts],
        "legacy_health_alerts_note": (
            "Legacy dashboard heuristics from ad_audit.engine.health_checks.run_health_checks (the Streamlit "
            "Dashboard shows the same alerts). They are not part of the campaign inference. duplication_rate is "
            "(platform-reported conversions - Shopify orders) / platform-reported conversions, from aggregate "
            "counts, not order-level matching. inflation_rate is (platform ROAS - estimated iROAS) / platform "
            "ROAS: estimated iROAS is that fraction BELOW platform ROAS. Quote these messages verbatim; do not "
            "re-express the percentages."),
        "mde80_definition": ("Minimum detectable effect at 80% power, two-sided 95%: SE x factor(t, residual df) "
                             "(scripts/run_v2_validation.mde_factor). A true iROAS that differs from a reference "
                             "value by less than this is unlikely to be distinguished from it."),
    }
    report = _clean(report)
    _apply_report_wording(report)
    markdown = render_markdown(report)

    out_dir = RUNS_DIR / run_id
    (out_dir / "inputs").mkdir(parents=True, exist_ok=True)
    for kind, (raw, _, source) in loaded.items():
        (out_dir / "inputs" / f"{kind}.csv").write_bytes(raw)
    (out_dir / "request.json").write_text(json.dumps(_clean({
        "contribution_margin": contribution_margin, "shopify_kind": shop_kind, "screening": assessment["answers"],
        "files": {k: v[2] for k, v in loaded.items()}}), indent=2) + "\n")
    (out_dir / "result.json").write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    (out_dir / "report.md").write_text(markdown)
    daily.to_csv(out_dir / "daily_panel.csv", index=False)

    n_est = sum(1 for c in campaigns if c["status"] == "estimated")
    status = (f"Audit complete: {len(campaigns)} campaign(s), {n_est} estimated, "
              f"{report['dataset']['days']} days, store iROAS "
              + (f"{store['true_incremental_roas']:.2f}x" if store.get("confidence_interval") else "unavailable")
              + f". Call get_report with report_id={run_id}.")
    return {"ok": True, "report_id": run_id, "status": status}


# ---------------------------------------------------------------- tool 3

def get_report(report_id: str) -> dict:
    if not isinstance(report_id, str) or not RUN_ID_RE.match(report_id):
        return {"ok": False, "errors": [f"Malformed report_id {report_id!r}"]}
    folder = RUNS_DIR / report_id
    if not (folder / "result.json").is_file():
        return {"ok": False, "errors": [f"No stored report with id {report_id}"]}
    report = json.loads((folder / "result.json").read_text())
    _apply_report_wording(report)
    return {"ok": True, "report": report, "report_markdown": render_markdown(report), "artifacts_dir": str(folder)}


# ---------------------------------------------------------------- rendering

def _x(v, digits=2):
    return "n/a" if v is None else f"{v:.{digits}f}x"


def _ci(ci):
    return "unavailable" if not ci else f"[{ci[0]:.2f}, {ci[1]:.2f}]x"


def _money(v):
    return "n/a" if v is None else f"${v:,.0f}"


def render_markdown(r: dict) -> str:
    s, d, rule = r["store"], r["dataset"], r["decision_rule"]
    w = r["warnings"]
    screening = r.get("screening") or budget_screening.not_screened()
    level = screening["risk_level"]
    store_label = s["effect_label"].replace("_", " ")
    if level == "high" and store_label == "positive":
        store_label += f" — downgraded at high endogeneity risk: {budget_screening.DOWNGRADE_PHRASE}"
    L = [f"# Ad attribution audit — report {r['report_id']}", "",
         f"Data window: {d['start']} to {d['end']} ({d['days']} days); Shopify input: {d['shopify_granularity']}. "
         f"Method: {r['engine']['method']} (model status: {r['engine']['model_status']}).", ""]
    if level == "high":
        L += [f"> **{budget_screening.HIGH_WARNING}**", ""]
    L += ["## Headline (all campaigns combined)", "",
         f"- Total ad spend: {_money(s['total_spend'])}",
         f"- Platform-reported ROAS: {_x(s['reported_roas'])} ({_money(s['reported_revenue'])} claimed by platforms)",
         f"- Estimated store incremental ROAS (iROAS): {_x(s['true_incremental_roas'])}, "
         f"95% CI {_ci(s['confidence_interval'])}, label: {store_label}"
         + (f", MDE80 {_x(s['mde80'])}" if s.get("mde80") is not None else ""),
         f"- Estimated incremental revenue: {_money(s['incremental_revenue'])}",
         f"- Estimated iROAS is {s['inflation_rate']:.0%} below platform-reported ROAS"
         if s.get("inflation_rate") is not None else "", ""]
    if s.get("note"):
        L += [f"> {s['note']}", ""]
    L += ["## Decision threshold", "", rule["rule"], ""]
    L += ["## Budget-behavior screening", ""]
    if not screening["provided"]:
        L.append(budget_screening.NOT_SCREENED_STATEMENT)
    else:
        L += [f"Endogeneity risk level: **{level}** (budget-behavior screening, intake Section B).", ""]
        L.extend(f"- Basis: {basis}" for basis in screening["basis"])
        if level == "low" and not budget_screening.PLATFORM_BIDDING_TOOLS.isdisjoint(screening["answers"]["b3a_tools"]):
            L += ["", budget_screening.LOW_BID_NOTE]
        if level == "medium" and screening["promotions"]:
            L += ["", "Promotion dates flagged from the intake calendar:", ""]
            for promotion in screening["promotions"]:
                raised = " (budget raised)" if promotion["budget_raised"] else ""
                L.append(f"- {promotion['dates']} — {promotion['event']}{raised}")
        if screening["prior_lift"] is not None:
            L += ["", budget_screening.prior_lift_comparison(screening["prior_lift"])]
        if level == "high":
            L += ["", "At this risk level, positive conclusions are downgraded and no directional action other "
                      "than kill is given; other priorities are shown as hold. A holdout is the top priority."]
    L.append("")
    L += ["## Per-campaign results", "", rule["action_notice"], "",
          "| Platform | Campaign | Spend | Platform ROAS | Est. iROAS | 95% CI | Label | MDE80 | Action |",
          "|---|---|---:|---:|---:|---|---|---:|---|"]
    for c in r["campaigns"]:
        label = c["effect_label"].replace("_", " ")
        if level == "high" and label == "positive":
            label += f" (downgraded: {budget_screening.DOWNGRADE_PHRASE})"
        L.append(f"| {c['platform']} | {c['campaign_name']} | {_money(c['total_spend'])} | {_x(c['reported_roas'])} | "
                 f"{_x(c['true_incremental_roas'])} | {_ci(c['confidence_interval'])} | "
                 f"{label} | {_x(c['mde80'])} | {c['action_display']} |")
    L += ["", "**Reasons for these priorities**", ""]
    for c in r["campaigns"]:
        reason = c["engine_action_reason"]
        note = label_action_note(c["confidence_interval"], rule["break_even_iroas"])
        if note:
            reason += f" {note}"
        L.append(f"- **{c['campaign_name']}** — {c['action_display']}: {reason}")
    if r["engine"]["validation_gate"] != "PASS":
        L += ["", f"**Validation hold.** The engine's validation gate is `{r['engine']['validation_gate']}` "
                  "(validation/v2-calibration-2026-11-09.md). Maintain all current budgets while gathering "
                  "evidence on the provisional priorities above."]
    inconclusive = [c for c in r["campaigns"] if c["effect_label"] in ("inconclusive", "unavailable")]
    if inconclusive:
        L += ["", "## Inconclusive / unavailable", ""]
        for c in inconclusive:
            if c["effect_label"] == "inconclusive":
                ci = c["confidence_interval"]
                L.append(f"- {c['campaign_name']}: 95% CI {_ci(ci)} includes zero but is not inside the +/-{r['decision_rule']['practical_zero_delta']}x "
                         f"practical-zero band (width {ci[1]-ci[0]:.2f}x; MDE80 {_x(c['mde80'])}). The data cannot "
                         "tell whether this campaign adds revenue; that is an answer, not a failure.")
            else:
                L.append(f"- {c['campaign_name']}: no estimate — " + "; ".join(c["warnings"] or ["inference unavailable"]))
    L += ["", "## Warnings", ""]
    for title, key in (("Data quality", "data_quality"), ("Data notes", "data_quality_notes"),
                       ("Model", "model"), ("Input files", "input_files")):
        for item in w.get(key, []):
            L.append(f"- {title}: {item}")
    if not any(w.get(k) for k in ("data_quality", "data_quality_notes", "model", "input_files")):
        L.append("- None from the data checks.")
    L += ["", "Standing identification limits of this method:", ""]
    L += [f"- {item}" for item in w["identification_limitations"]]
    md = r["model_diagnostics"]
    if md.get("status") == "estimated":
        L += ["", "## Model diagnostics", "",
              f"n_obs={md.get('n_obs')}, parameters={md.get('n_parameters')}, residual df={md.get('residual_df')}, "
              f"R²={md.get('r_squared'):.3f}, Durbin-Watson={md.get('durbin_watson'):.2f}, "
              f"condition number={md.get('condition_number'):.1f}, controls={', '.join(md.get('controls', []))}."]
    if r.get("legacy_health_alerts"):
        L += ["", "## Legacy dashboard alerts (not campaign inference)", "", r["legacy_health_alerts_note"], ""]
        L += [f"- {a['severity']}: {a['title']} — {a['message']}" for a in r["legacy_health_alerts"]]
    appendix_campaigns = ((c["campaign_name"], c["total_spend"], c["confidence_interval"]) for c in r["campaigns"])
    lead = budget_screening.MEDIUM_HOLDOUT_LEAD if level == "medium" else None
    L += ["", f"MDE80: {r['mde80_definition']}", "", appendix_markdown(appendix_campaigns, lead=lead)]
    return "\n".join(x for x in L if x is not None) + "\n"
