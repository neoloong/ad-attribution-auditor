"""Verify the standalone report and compare its browser rules to the engine."""

from copy import deepcopy
from html import unescape
import json
from pathlib import Path
import re
import shutil
import subprocess

import pytest

from ad_audit.engine.models import classify_effect_interval
from ad_audit.report import screening
from ad_audit.report.holdout import ACTION_NOTICE, TITLE, cost_example
from ad_audit.report.html_report import render_html_report, write_html_report
from scripts.gate1_pdf import ACTION_RULE, label_action_note, provisional_action_for_interval


@pytest.fixture
def report():
    campaigns = []
    for name, platform, spend, reported_roas, estimate, ci, se, mde, revenue, warnings in (
        ("Prospecting – été", "meta", 16412.55, 3.125, -0.1389, [-1.5383, 1.2608], 0.62, 1.78, -2279.70,
         ["Campaign spend is correlated with demand."]),
        ("Brand search", "google_ads", 9234.5, 4.125, 2.70815, [1.8344, 3.5819], 0.44, 1.24, 25009.81, []),
        ("Retargeting", "meta", 2050, 2.675, None, None, None, None, None, ["Insufficient delivery.", "No interval."]),
    ):
        action, reason = provisional_action_for_interval(ci, 2.5)
        campaigns.append({
            "campaign_name": name, "platform": platform, "total_spend": spend, "reported_roas": reported_roas,
            "true_incremental_roas": estimate, "confidence_interval": ci, "standard_error": se, "mde80": mde,
            "incremental_revenue": revenue, "status": "estimated" if ci else "unavailable", "warnings": warnings,
            "effect_label": classify_effect_interval(ci), "action": action, "engine_action": action,
            "engine_action_reason": reason, "action_display": f"{action} (provisional)",
        })

    return {
        "report_id": "20261123T034500Z-f41e3be9",
        "created_utc": "2026-11-23T03:45:00+00:00",
        "engine": {"method": "joint_revenue_ols_hc3", "model_status": "estimated", "validation_gate": "FAIL"},
        "inputs": {"meta_ads": {"file": "méta.csv", "sha256": "1234567890abcdef" * 4}},
        "dataset": {"start": "2026-08-01", "end": "2026-09-29", "days": 60, "shopify_granularity": "daily"},
        "decision_rule": {
            "contribution_margin": 0.4, "margin_source": "assumed", "break_even_iroas": 2.5,
            "practical_zero_delta": 0.2, "action_notice": ACTION_NOTICE,
            "rule": "Assumed contribution margin: 40%. Break-even iROAS = 1/margin = 2.50x. " + ACTION_RULE,
        },
        "store": {
            "total_spend": 27697.05, "reported_roas": 3.43, "reported_revenue": 94940.88,
            "true_incremental_roas": 1.82, "confidence_interval": [0.83, 2.81], "effect_label": "positive",
            "mde80": 1.42, "incremental_revenue": 50408.63, "inflation_rate": 0.47, "note": "Fixture store note.",
        },
        "campaigns": campaigns,
        "screening": None,
        "warnings": {
            "data_quality": ["Some Shopify dates are missing."], "data_quality_notes": ["Daily Shopify input."],
            "model": ["Residual diagnostic warning."], "input_files": ["File metadata unavailable."],
            "campaign": {campaign["campaign_name"]: campaign["warnings"] for campaign in campaigns if campaign["warnings"]},
            "identification_limitations": ["Omitted demand factors can affect the estimate."],
        },
        "model_diagnostics": {
            "status": "estimated", "n_obs": 60, "n_parameters": 8, "residual_df": 52, "r_squared": 0.83251,
            "durbin_watson": 1.874, "condition_number": 118.218, "controls": ["weekday", "trend"],
            "optional_diagnostic": None,
        },
        "legacy_health_alerts": [{"severity": "info", "title": "Spend", "message": "Check Meta & Google totals."}],
        "legacy_health_alerts_note": "Legacy alerts from the dashboard.",
        "mde80_definition": "Minimum detectable effect at 80% power, two-sided 95%.",
    }


@pytest.fixture
def high_report(report):
    high = deepcopy(report)
    high["screening"] = {
        "provided": True, "risk_level": "high", "basis": ["Demand-following spend."],
        "answers": {"b3a_tools": ["meta_rules"]}, "promotions": [], "prior_lift": None,
    }
    for campaign in high["campaigns"]:
        action = screening.presentation_action(campaign["engine_action"], "high")
        campaign["action_display"] = f"{action} (provisional)"
    return high


def _embedded_data(document):
    return re.search(r'<script type="application/json" id="report-data">(.*?)</script>', document, re.S)[1]


def test_embedded_json_round_trip(report):
    report["store"]["note"] = "Préparé </script><!--<script>unsafe()</script> and </SCRIPT>"
    document = render_html_report(report)
    data = _embedded_data(document)
    assert data == json.dumps(report, ensure_ascii=False).replace("</", r"<\/").replace("<!--", r"\u003c!--")
    assert json.loads(data) == report
    assert "<script>unsafe()" not in document.split('<script type="application/json"', 1)[0]


def test_report_is_self_contained(report):
    report["inputs"]["meta_ads"]["file"] = "https://example.test/méta.csv"
    report["store"]["note"] = "Notes at http://example.test"
    document = render_html_report(report)
    assert "http://" not in document
    assert "https://" not in document
    assert json.loads(_embedded_data(document)) == report
    assert report["inputs"]["meta_ads"]["file"] in unescape(document)


def test_headline_and_static_sections(report, high_report):
    document = render_html_report(report)
    static = unescape(document.split('<script type="application/json"', 1)[0])
    for text in (
        "AD ATTRIBUTION AUDITOR", "Ad attribution audit", f"Report {report['report_id']}", "Prepared 2026-11-23",
        "Data window: 2026-08-01 to 2026-09-29 (60 days); Shopify input: daily.",
        "Method: joint_revenue_ols_hc3 (model status: estimated).",
        "$27,697", "3.43x", "$94,941 claimed by platforms", "1.82x", "95% CI [0.83, 2.81]x, label: positive, MDE80 1.42x",
        "$50,409", "Estimated iROAS is 47% below platform-reported ROAS", "Fixture store note.",
        report["decision_rule"]["rule"], screening.NOT_SCREENED_STATEMENT, ACTION_NOTICE,
        "Validation hold.", "Maintain all current budgets while gathering evidence on the provisional priorities above.",
        "Prospecting – été: 95% CI [-1.54, 1.26]x includes zero but is not inside the +/-0.2x practical-zero band "
        "(width 2.80x; MDE80 1.78x).",
        "Retargeting: no estimate — Insufficient delivery.; No interval.",
        "Data quality: Some Shopify dates are missing.", "Data notes: Daily Shopify input.",
        "Model: Residual diagnostic warning.", "Input files: File metadata unavailable.",
        "Omitted demand factors can affect the estimate.",
        "n_obs=60, parameters=8, residual df=52, R²=0.833, Durbin-Watson=1.87, condition number=118.2, controls=weekday, trend.",
        "Legacy alerts from the dashboard.", "info: Spend — Check Meta & Google totals.",
        f"MDE80: {report['mde80_definition']}", TITLE, "1234567890ab",
    ):
        assert text in static
    for campaign in report["campaigns"]:
        assert f"<td>{campaign['action_display']}</td>" in static
        assert cost_example(campaign["total_spend"], campaign["confidence_interval"]) in static

    appendix = static.split("<h2>Data appendix</h2>", 1)[1]
    for campaign in report["campaigns"]:
        assert f"<td>{campaign['campaign_name']}</td><td>{campaign['total_spend']}</td>" in appendix
    for key, value in report["model_diagnostics"].items():
        expected = {"controls": "weekday, trend", "optional_diagnostic": "n/a"}.get(key, str(value))
        assert f"<td>{key}</td><td>{expected}</td>" in appendix

    high_static = unescape(render_html_report(high_report).split('<script type="application/json"', 1)[0])
    assert screening.HIGH_WARNING in high_static
    assert f"positive — downgraded at high endogeneity risk: {screening.DOWNGRADE_PHRASE}" in high_static
    assert f"<td>positive (downgraded: {screening.DOWNGRADE_PHRASE})</td>" in high_static
    assert "Basis: Demand-following spend." in high_static
    assert screening.NOT_SCREENED_STATEMENT not in high_static


def test_low_and_medium_screening_notes(report):
    report["warnings"] = {"identification_limitations": []}
    report["screening"] = {
        "provided": True, "risk_level": "low", "basis": ["Intake response."],
        "answers": {"b3a_tools": ["google_smart_bidding"]},
        "promotions": [{"dates": "2026-08-04", "event": "Summer sale", "budget_raised": True}],
        "prior_lift": {"scope": "Store", "lift": 1.2, "ci_low": 0.8, "ci_high": 1.6},
    }
    low = unescape(render_html_report(report).split('<script type="application/json"', 1)[0])
    assert "None from the data checks." in low
    assert screening.LOW_BID_NOTE in low
    assert screening.prior_lift_comparison(report["screening"]["prior_lift"]) in low
    assert "Promotion dates flagged" not in low

    report["screening"]["risk_level"] = "medium"
    medium = unescape(render_html_report(report).split('<script type="application/json"', 1)[0])
    assert "Promotion dates flagged from the intake calendar:" in medium
    assert "2026-08-04 — Summer sale (budget raised)" in medium
    assert f"<h2>{TITLE}</h2><p>{screening.MEDIUM_HOLDOUT_LEAD}</p>" in medium
    assert screening.LOW_BID_NOTE not in medium


def test_data_appendix_accepts_arbitrary_json_diagnostics(report):
    report["model_diagnostics"]["extra_list"] = [12, None, True, {"a": ["é"]}, [1, 2]]
    report["model_diagnostics"]["extra_object"] = {"key": False}
    document = unescape(render_html_report(report).split('<script type="application/json"', 1)[0])
    assert '<td>extra_list</td><td>12, n/a, true, {"a": ["é"]}, [1, 2]</td>' in document
    assert '<td>extra_object</td><td>{"key": false}</td>' in document


def test_write_html_report_returns_utf8_path(report, tmp_path):
    path = tmp_path / "report.html"
    result = write_html_report(report, str(path))
    assert isinstance(result, Path)
    assert result == path
    assert path.read_bytes() == render_html_report(report).encode("utf-8")


CI_VECTORS = [
    [-1.5383, 1.2608], [1.8344, 3.5819], [2.3202, 3.1837], [2.5, 3.0],
    [1.0, 2.5], [3.125, 4.0], [0.125, 1.125], [2.675, 3.0], [-0.125, 0.125],
    [0.5, 0.5], [0.0, 0.0], [-2.0, -1.0], [4.0, 3.0], None,
]

HOLDOUT_VECTORS = [
    [16412.55, [-1.5383, 1.2608], 20, 2, 60],
    [9234.5, [1.8344, 3.5819], 5, 8, 90],
    [1895.32, [-2.0, -1.0], 50, 1, 7],
    [2050, None, 20, 2, 60],
    [0, [1.0, 2.5], 20, 2, 60],
    [None, [1.0, 2.5], 20, 2, 60],
    [-100, [1.0, 2.5], 20, 2, 60],
]

FORMAT_VECTORS = [
    3.125, 0.375, 2.675, -0.125, 16412.55, 1234.5, -1234.5, 0.0, -0.0, -5e-324, -0.0049,
    999.995, 999999.5, 1e21, 1.7976931348623157e308,
]

NODE_HARNESS = """
const {margins, intervals, presentations, holdouts, numbers} =
  JSON.parse(require("node:fs").readFileSync(process.argv[2], "utf8"));
const grid = margins.map(pct => {
  const threshold = 1 / (pct / 100);
  return intervals.map(ci => [...provisionalActionForInterval(ci, threshold), labelActionNote(ci, threshold)]);
});
const invalidIntervals = [null, {}, "0,1", [], [0], [1, 2, 3], [0, NaN], [0, Infinity], ["0", 1]];
console.log(JSON.stringify({
  grid,
  presentations: presentations.map(args => presentationAction(...args)),
  holdouts: holdouts.map(([spend, ci, ...args]) =>
    [holdoutPausedSpend(spend, ...args), holdoutCost(spend, ci, ...args)]),
  numbers: numbers.map(value => [fmt2(value), fmt0(value)]),
  labels: intervals.map(ci => classifyEffectInterval(ci)),
  invalidLabels: invalidIntervals.map(ci => classifyEffectInterval(ci)),
  displayedLabels: ["positive", "practically_zero"].map(label => displayLabel(label, "high")),
  downgradePhrase: DOWNGRADE_PHRASE,
}));
"""


def _run_ported_rules(report, tmp_path, *, margins, intervals, presentations=(), holdouts=(), numbers=()):
    node = shutil.which("node")
    if node is None:
        pytest.skip("node is not on PATH")

    document = render_html_report(report)
    rules = re.search(r"// === BEGIN PORTED RULES ===\n(.*?)\n// === END PORTED RULES ===", document, re.S)[1]
    harness = tmp_path / "harness.cjs"
    harness.write_text(rules + "\n" + NODE_HARNESS, encoding="utf-8")
    vectors = tmp_path / "vectors.json"
    vectors.write_text(json.dumps({
        "margins": margins, "intervals": intervals, "presentations": presentations,
        "holdouts": holdouts, "numbers": numbers,
    }), encoding="utf-8")

    result = subprocess.run([node, str(harness), str(vectors)], capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def test_javascript_grid_matches_python_rules(report, tmp_path):
    margins = list(range(10, 91))
    presentations = [(action, level) for action in ("keep", "kill", "hold") for level in (None, "low", "medium", "high")]
    actual = _run_ported_rules(
        report, tmp_path, margins=margins, intervals=CI_VECTORS, presentations=presentations,
        holdouts=HOLDOUT_VECTORS, numbers=FORMAT_VECTORS,
    )
    assert len(actual["grid"]) == len(margins)
    for pct, row in zip(margins, actual["grid"]):
        threshold = 1 / (pct / 100)
        assert len(row) == len(CI_VECTORS)
        for ci, cell in zip(CI_VECTORS, row):
            expected = [*provisional_action_for_interval(ci, threshold), label_action_note(ci, threshold)]
            assert cell == expected, f"margin={pct}%, interval={ci}"
    assert actual["presentations"] == [screening.presentation_action(*args) for args in presentations]

    expected_holdouts = []
    for spend, ci, share, weeks, days in HOLDOUT_VECTORS:
        paused = None if spend is None or spend <= 0 else spend / (days / 7) * weeks * (share / 100)
        cost = None if paused is None or ci is None else [paused * ci[0], paused * ci[1]]
        expected_holdouts.append([paused, cost])
    assert actual["holdouts"] == expected_holdouts
    assert actual["numbers"] == [[f"{value:.2f}", f"{value:,.0f}"] for value in FORMAT_VECTORS]
    assert actual["labels"] == [classify_effect_interval(ci) for ci in CI_VECTORS]
    assert actual["invalidLabels"] == ["unavailable"] * 9
    assert actual["displayedLabels"] == [f"positive (downgraded: {screening.DOWNGRADE_PHRASE})", "practically zero"]
    assert actual["downgradePhrase"] == screening.DOWNGRADE_PHRASE


def test_javascript_default_margin_matches_report(report, tmp_path):
    campaigns = report["campaigns"]
    intervals = [campaign["confidence_interval"] for campaign in campaigns]
    actual = _run_ported_rules(report, tmp_path, margins=[40], intervals=intervals)["grid"][0]
    assert [action for action, _, _ in actual] == ["kill", "hold", "hold"]
    for campaign, (action, reason, note) in zip(campaigns, actual):
        ci = campaign["confidence_interval"]
        expected_action, expected_reason = provisional_action_for_interval(ci, 2.5)
        expected_note = label_action_note(ci, 2.5)
        assert action == expected_action == campaign["engine_action"]
        assert reason == expected_reason == campaign["engine_action_reason"]
        assert " ".join(filter(None, (reason, note))) == " ".join(
            filter(None, (campaign["engine_action_reason"], expected_note))
        )
