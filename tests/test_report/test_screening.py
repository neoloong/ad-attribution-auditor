"""Section B classification, stored intake, and report presentation."""

from copy import deepcopy
import hashlib
import json
import re

import pytest

from ad_audit.report.holdout import TITLE
from ad_audit.report.screening import (
    DOWNGRADE_PHRASE,
    HIGH_WARNING,
    LOW_BID_NOTE,
    MEDIUM_HOLDOUT_LEAD,
    NOT_SCREENED_STATEMENT,
    assess_screening,
    not_screened,
    presentation_action,
    validate_screening,
)
from agent_native import audit_service, mcp_server
from scripts.gate1_pdf import render_report
from tests.test_report.test_sample_pdf import sample_data


ROW_5 = {
    "b1_setting": "fixed_monthly", "b1_frequency": "weekly", "b2_changers": ["person"],
    "b2_driver": "sales_roas", "b2_lag": "within_week", "b3a_tools": ["none"],
    "b3b_promo_changes": "no", "b3c_sell_well_add": "no",
}
PROMOTION = {"dates": "2026-11-19 to 2026-11-23", "event": "Holiday sale", "budget_raised": True}
LIFT = {"scope": "Google Search", "lift": 1.15, "ci_low": 0.8, "ci_high": 1.5}
ROW_1 = {
    **ROW_5, "b1_setting": "fully_dynamic", "b1_frequency": "daily",
    "b2_lag": "same_day", "b3c_sell_well_add": "written_rule",
}
ROW_2 = {
    **ROW_5, "b1_setting": "fixed_adjusted", "b1_frequency": "several_times_week",
    "b2_changers": ["predefined_rules"], "b2_lag": "next_day", "b3a_tools": ["meta_rules"],
    "b3b_promo_changes": "yes",
}
ROW_3 = {
    **ROW_5, "b1_setting": "fixed_adjusted", "b3a_tools": ["google_smart_bidding"],
    "b4_promotions": [PROMOTION],
}
ROW_4 = {**ROW_5, "b1_setting": "fully_dynamic", "b2_driver": "planned_calendar", "b5_prior_experiment": "yes"}
ROW_6 = {
    **ROW_5, "b2_changers": ["person", "platform_auto"],
    "b3a_tools": ["meta_advantage_plus", "google_smart_bidding"],
    "b6_pauses": [{"campaign": "Search", "reason": "planned"}, {"campaign": "Social", "reason": "policy"}],
}


@pytest.mark.parametrize("answers,level", [
    (ROW_1, "high"), (ROW_2, "high"), (ROW_3, "medium"),
    (ROW_4, "medium"), (ROW_5, "low"), (ROW_6, "low"),
])
def test_annex_rows(answers, level):
    assessment = assess_screening(answers)
    assert assessment["risk_level"] == level
    assert not assessment["not_sure_bump"]
    assert all(reason.startswith("Annex ") for reason in assessment["basis"])


def test_same_day_predefined_rules_override_other_answers():
    assessment = assess_screening({**ROW_5, "b2_lag": "same_day", "b2_driver": "planned_calendar",
                                   "b2_changers": ["person", "predefined_rules"]})
    assert assessment["risk_level"] == "high"
    assert assessment["basis"][0].startswith("Annex edge rule:")


@pytest.mark.parametrize("answers,level", [
    ({**ROW_5, "b2_lag": "not_sure"}, "medium"),
    ({**ROW_3, "b3c_sell_well_add": "not_sure"}, "high"),
    ({**ROW_2, "b3c_sell_well_add": "not_sure"}, "high"),
])
def test_not_sure_raises_risk_up_to_high(answers, level):
    assessment = assess_screening(answers)
    assert assessment["risk_level"] == level
    assert assessment["not_sure_bump"]
    assert assessment["basis"][-1].startswith("Annex edge rule:")


@pytest.mark.parametrize("overrides,level,basis", [
    ({"b2_lag": "next_day", "b1_setting": "fully_dynamic", "b1_frequency": "daily"}, "high", "interpretation"),
    ({"b2_lag": "next_day"}, "medium", "fast sales/ROAS"),
    ({"b3c_sell_well_add": "informal_habit"}, "medium", "weekly changes"),
    ({"b2_lag": "next_day", "b2_driver": "planned_calendar"}, "medium", "fallback for unlisted combinations"),
])
def test_annex_signal_weighting_and_fallback(overrides, level, basis):
    assessment = assess_screening({**ROW_5, **overrides})
    assert assessment["risk_level"] == level
    assert basis in assessment["basis"][0]


@pytest.mark.parametrize("answers,message", [
    ({**ROW_5, "b1_setting": "sometimes"}, "b1_setting must be one of"),
    ({key: value for key, value in ROW_5.items() if key != "b2_lag"}, "missing required field.*b2_lag"),
    ({**ROW_5, "b1_other": "no"}, "unknown field.*b1_other"),
    ({**ROW_5, "b4_promotions": [{**PROMOTION, "budget_raised": "yes"}]}, r"b4_promotions\[0\].budget_raised"),
    ({**ROW_5, "b5_lift": {**LIFT, "ci_high": float("nan")}}, "b5_lift.ci_high must be a finite number"),
])
def test_invalid_screening_is_rejected(answers, message):
    with pytest.raises(ValueError, match=message):
        validate_screening(answers)


@pytest.mark.parametrize("action,level,expected", [
    ("keep", "high", "hold"), ("kill", "high", "kill"), ("hold", "high", "hold"),
    ("keep", "medium", "keep"), ("keep", "low", "keep"), ("keep", None, "keep"),
])
def test_presentation_action(action, level, expected):
    assert presentation_action(action, level) == expected


@pytest.fixture
def report():
    metrics = {"total_spend": 100, "reported_roas": 3.5, "true_incremental_roas": 3.1,
               "confidence_interval": [2.8, 3.4], "effect_label": "positive"}
    return {
        "report_id": "sample",
        "dataset": {"start": "2026-11-01", "end": "2026-11-03", "days": 3, "shopify_granularity": "daily"},
        "store": {**metrics, "reported_revenue": 350, "incremental_revenue": 310},
        "engine": {"method": "OLS", "model_status": "estimated", "validation_gate": "FAIL"},
        "decision_rule": {"contribution_margin": 0.4, "margin_source": "assumed", "break_even_iroas": 2.5,
                          "rule": "Break-even rule", "action_notice": "Provisional priorities"},
        "campaigns": [{**metrics, "platform": "Google", "campaign_name": "Search", "mde80": None,
                       "action_display": "keep (provisional)", "engine_action_reason": "CI above break-even."}],
        "warnings": {"identification_limitations": []},
        "model_diagnostics": {},
        "mde80_definition": "Minimum detectable effect at 80% power",
    }


def test_high_markdown_warns_before_headline_and_downgrades_positive_labels(report):
    report["screening"] = assess_screening(ROW_1)
    audit_service._apply_report_wording(report)
    markdown = audit_service.render_markdown(report)
    lines = markdown.splitlines()
    assert lines.index(f"> **{HIGH_WARNING}**") < lines.index("## Headline (all campaigns combined)")
    assert any(line.startswith("- Estimated store incremental ROAS") and DOWNGRADE_PHRASE in line for line in lines)
    assert any(f"| positive (downgraded: {DOWNGRADE_PHRASE}) | n/a | hold (provisional) |" in line for line in lines)
    assert "## Budget-behavior screening\n\nEndogeneity risk level: **high**" in markdown


def test_markdown_discloses_missing_screening(report):
    assert NOT_SCREENED_STATEMENT in audit_service.render_markdown(report).splitlines()


def test_medium_markdown_flags_promotions_and_prior_lift_and_leads_with_holdout(report):
    report["screening"] = assess_screening({**ROW_4, "b4_promotions": [PROMOTION], "b5_lift": LIFT})
    markdown = audit_service.render_markdown(report)
    section = markdown.split("## Budget-behavior screening\n", 1)[1].split("## Per-campaign results", 1)[0]
    assert "Promotion dates flagged from the intake calendar:" in section
    assert "- 2026-11-19 to 2026-11-23 — Holiday sale (budget raised)" in section
    assert "Google Search: measured lift 1.15x, interval [0.80, 1.50]x" in section
    assert f"## {TITLE}\n\n{MEDIUM_HOLDOUT_LEAD}\n\n**Purpose.**" in markdown


def test_high_wording_preserves_underlying_actions_and_reasons(report):
    keep = report["campaigns"][0]
    kill = {**keep, "campaign_name": "Brand", "confidence_interval": [0.5, 1.2]}
    report["campaigns"].append(kill)
    audit_service._apply_report_wording(report)
    before = deepcopy(report["campaigns"])
    report["screening"] = assess_screening(ROW_1)
    audit_service._apply_report_wording(report)
    assert before[0]["action"] == "keep"
    assert before[1]["action"] == "kill"
    assert keep == {**before[0], "action_display": "hold (provisional)"}
    assert kill == before[1]
    assert kill["action_display"] == "kill (provisional)"


def pdf_text(path):
    # The local renderer uses uncompressed Helvetica text streams.
    chunks = re.findall(rb'\(((?:\\.|[^\\)])*)\) Tj', path.read_bytes())
    return ' '.join(re.sub(rb'\\([\\()])', rb'\1', chunk).decode('cp1252') for chunk in chunks)


def test_high_pdf_warns_and_updates_badge_and_label(tmp_path):
    path = tmp_path / "high.pdf"
    data = sample_data()
    data["gate"] = "FAIL"
    campaign = data["campaign_results"][0]
    campaign["incremental_roas"]["confidence_interval"] = [2.8, 3.4]
    render_report(data, path, screening=assess_screening(ROW_1))
    text = pdf_text(path)
    assert HIGH_WARNING in text
    assert f"{campaign['campaign']} hold (provisional)" in text
    assert "Validation hold. Provisional priority: keep." in text
    assert "Evidence label: positive - downgraded (high endogeneity risk)." in text


def test_low_pdf_explains_platform_bidding(tmp_path):
    path = tmp_path / "low.pdf"
    render_report(sample_data(), path, screening=assess_screening(ROW_6))
    assert LOW_BID_NOTE in pdf_text(path)


def test_medium_pdf_includes_promotion_lift_and_holdout_lead(tmp_path):
    path = tmp_path / "medium.pdf"
    render_report(sample_data(), path, screening=assess_screening({**ROW_3, "b5_lift": LIFT}))
    text = pdf_text(path)
    assert "Promotion dates flagged from the intake calendar: 2026-11-19 to 2026-11-23 (Holiday sale)" in text
    assert "Google Search: measured lift 1.15x, interval [0.80, 1.50]x" in text
    assert f"{MEDIUM_HOLDOUT_LEAD} Purpose" in text


def test_pdf_without_screening_has_no_screening_text(tmp_path):
    path = tmp_path / "original.pdf"
    render_report(sample_data(), path, screening=None)
    text = pdf_text(path)
    assert "HIGH ENDOGENEITY RISK" not in text
    assert "Budget-behavior screening" not in text


def test_pdf_explicitly_discloses_not_screened_assessment(tmp_path):
    path = tmp_path / "not-screened.pdf"
    render_report(sample_data(), path, screening=not_screened())
    text = pdf_text(path)
    assert "Budget-behavior screening: not provided - no endogeneity risk level assigned." in text
    assert "Screening was not provided; no endogeneity risk level was assigned." in text


def test_mcp_audit_persists_screening_and_hashes_canonical_answers(tmp_path, monkeypatch):
    monkeypatch.setattr(audit_service, "RUNS_DIR", tmp_path)
    monkeypatch.setattr(mcp_server, "_service", audit_service)
    meta = ("Day,Campaign name,Amount spent (USD),Purchases,Purchase conversion value\n"
            "2026-11-01,Prospecting,15,1,75\n2026-11-02,Prospecting,12,1,60\n2026-11-03,Prospecting,25,2,100\n")
    shop = ("date,orders,revenue,currency\n"
            "2026-11-01,4,200,USD\n2026-11-02,3,120,USD\n2026-11-03,5,320,USD\n")
    args = {"meta_ads": {"content": meta}, "shopify": {"kind": "shopify_daily", "content": shop}}
    run_schema = next(tool["inputSchema"] for tool in mcp_server.TOOLS if tool["name"] == "run_audit")
    assert run_schema["properties"]["screening"]["type"] == "object"
    assert "screening" not in run_schema["required"]

    error = mcp_server.call_tool("run_audit", {**args, "screening": {}})
    assert error["isError"]
    assert error["structuredContent"]["status"].startswith("rejected: screening:")

    unscreened = mcp_server.call_tool("run_audit", args)["structuredContent"]
    screened = mcp_server.call_tool("run_audit", {**args, "screening": ROW_1})["structuredContent"]
    assert unscreened["ok"] and screened["ok"]
    normalized = validate_screening(ROW_1)
    digest_material = (meta + shop + repr(None)).encode()
    assert unscreened["report_id"].endswith(hashlib.sha256(digest_material).hexdigest()[:8])
    digest_material += json.dumps(normalized, sort_keys=True).encode()
    assert screened["report_id"].endswith(hashlib.sha256(digest_material).hexdigest()[:8])

    request = json.loads((tmp_path / screened["report_id"] / "request.json").read_text())
    assert request["screening"] == normalized
    loaded = audit_service.get_report(screened["report_id"])
    assert loaded["report"]["screening"] == assess_screening(ROW_1)
    assert HIGH_WARNING in loaded["report_markdown"]
    assert audit_service.get_report(unscreened["report_id"])["report"]["screening"] == not_screened()
