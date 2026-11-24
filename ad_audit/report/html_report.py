"""Render a result.json audit report as a standalone, interactive document."""

import json
from html import escape
from pathlib import Path

from ad_audit.report import screening as budget_screening
from ad_audit.report.holdout import ACTION_NOTICE, SECTIONS, TITLE, cost_example


def _x(v):
    return "n/a" if v is None else f"{v:.2f}x"


def _ci(ci):
    return "unavailable" if not ci else f"[{ci[0]:.2f}, {ci[1]:.2f}]x"


def _money(v):
    return "n/a" if v is None else f"${v:,.0f}"


def _escape(value):
    # Keep URL-like text legible without emitting literal URLs in the source.
    return escape(str(value)).replace("http://", "http&#58;//").replace("https://", "https&#58;//")


def _section(title, body):
    return f"<section><h2>{_escape(title)}</h2>{body}</section>"


def _paragraph(text):
    return f"<p>{_escape(text)}</p>"


def _list(items):
    entries = "".join(f"<li>{_escape(item)}</li>" for item in items)
    return f"<ul>{entries}</ul>"


def _table(title, headings, rows):
    headers = "".join(f'<th scope="col">{_escape(heading)}</th>' for heading in headings)
    body = "".join(
        "<tr>" + "".join(f"<td>{_escape(value)}</td>" for value in row) + "</tr>"
        for row in rows
    )
    return (f'<div class="table-scroll" role="region" aria-label="{_escape(title)}" tabindex="0">'
            f"<table><thead><tr>{headers}</tr></thead><tbody>{body}</tbody></table></div>")


def _dataset_line(dataset):
    return (f"Data window: {dataset['start']} to {dataset['end']} ({dataset['days']} days); "
            f"Shopify input: {dataset['shopify_granularity']}.")


def _headline(store, level):
    label = store["effect_label"].replace("_", " ")
    if level == "high" and label == "positive":
        label += f" — downgraded at high endogeneity risk: {budget_screening.DOWNGRADE_PHRASE}"
    estimate_detail = f"95% CI {_ci(store['confidence_interval'])}, label: {label}"
    if store.get("mde80") is not None:
        estimate_detail += f", MDE80 {_x(store['mde80'])}"
    figures = (
        ("Total ad spend", _money(store["total_spend"]), ""),
        ("Platform-reported ROAS", _x(store["reported_roas"]),
         f"{_money(store['reported_revenue'])} claimed by platforms"),
        ("Estimated store incremental ROAS (iROAS)", _x(store["true_incremental_roas"]), estimate_detail),
        ("Estimated incremental revenue", _money(store["incremental_revenue"]), ""),
    )
    body = ['<dl class="figures">']
    for heading, value, detail in figures:
        context = f'<span>{_escape(detail)}</span>' if detail else ""
        body.append(f"<div><dt>{_escape(heading)}</dt><dd><strong>{_escape(value)}</strong>{context}</dd></div>")
    body.append("</dl>")
    if store.get("inflation_rate") is not None:
        body.append(_paragraph(f"Estimated iROAS is {store['inflation_rate']:.0%} below platform-reported ROAS"))
    if store.get("note"):
        body.append(f'<p class="notice">{_escape(store["note"])}</p>')
    body.append('<div id="headline-chart"></div>')
    return _section("Headline (all campaigns combined)", "".join(body))


def _screening(assessment, level):
    if not assessment["provided"]:
        return _section("Budget-behavior screening", _paragraph(budget_screening.NOT_SCREENED_STATEMENT))

    body = [f"<p>Endogeneity risk level: <strong>{_escape(level)}</strong> "
            "(budget-behavior screening, intake Section B).</p>",
            _list(f"Basis: {basis}" for basis in assessment["basis"])]
    if level == "low" and not budget_screening.PLATFORM_BIDDING_TOOLS.isdisjoint(assessment["answers"]["b3a_tools"]):
        body.append(_paragraph(budget_screening.LOW_BID_NOTE))
    if level == "medium" and assessment["promotions"]:
        body.append(_paragraph("Promotion dates flagged from the intake calendar:"))
        body.append(_list(
            f"{promotion['dates']} — {promotion['event']}" + (" (budget raised)" if promotion["budget_raised"] else "")
            for promotion in assessment["promotions"]
        ))
    if assessment["prior_lift"] is not None:
        body.append(_paragraph(budget_screening.prior_lift_comparison(assessment["prior_lift"])))
    if level == "high":
        body.append(_paragraph("At this risk level, positive conclusions are downgraded and no directional action other "
                               "than kill is given; other priorities are shown as hold. A holdout is the top priority."))
    return _section("Budget-behavior screening", "".join(body))


def _campaign_row(campaign, level):
    label = campaign["effect_label"].replace("_", " ")
    if level == "high" and label == "positive":
        label += f" (downgraded: {budget_screening.DOWNGRADE_PHRASE})"
    return (
        campaign["platform"], campaign["campaign_name"], _money(campaign["total_spend"]),
        _x(campaign["reported_roas"]), _x(campaign["true_incremental_roas"]), _ci(campaign["confidence_interval"]),
        label, _x(campaign["mde80"]), campaign["action_display"],
    )


def _inconclusive(campaigns, delta):
    items = []
    for campaign in campaigns:
        name = campaign["campaign_name"]
        label = campaign["effect_label"]
        if label == "inconclusive":
            ci = campaign["confidence_interval"]
            items.append(
                f"{name}: 95% CI {_ci(ci)} includes zero but is not inside the +/-{delta}x "
                f"practical-zero band (width {ci[1] - ci[0]:.2f}x; MDE80 {_x(campaign['mde80'])}). The data cannot "
                "tell whether this campaign adds revenue; that is an answer, not a failure."
            )
        elif label == "unavailable":
            items.append(f"{name}: no estimate — " + "; ".join(campaign["warnings"] or ["inference unavailable"]))
    return _section("Inconclusive / unavailable", _list(items)) if items else ""


def _warnings(warnings):
    items = [
        f"{title}: {item}"
        for title, key in (("Data quality", "data_quality"), ("Data notes", "data_quality_notes"),
                           ("Model", "model"), ("Input files", "input_files"))
        for item in warnings.get(key, [])
    ]
    return _section("Warnings", _list(items or ["None from the data checks."])
                    + _paragraph("Standing identification limits of this method:")
                    + _list(warnings["identification_limitations"]))


def _diagnostic_value(value):
    if value is None:
        return "n/a"
    if isinstance(value, list):
        return ", ".join(
            json.dumps(item, ensure_ascii=False) if isinstance(item, list) else _diagnostic_value(item)
            for item in value
        )
    if isinstance(value, (dict, bool)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def _diagnostics(diagnostics):
    if diagnostics.get("status") != "estimated":
        return ""

    def decimal(key, digits):
        value = diagnostics.get(key)
        return f"{value:.{digits}f}" if type(value) in (int, float) else _diagnostic_value(value)

    return _section("Model diagnostics", _paragraph(
        f"n_obs={diagnostics.get('n_obs')}, parameters={diagnostics.get('n_parameters')}, "
        f"residual df={diagnostics.get('residual_df')}, R²={decimal('r_squared', 3)}, "
        f"Durbin-Watson={decimal('durbin_watson', 2)}, condition number={decimal('condition_number', 1)}, "
        f"controls={_diagnostic_value(diagnostics.get('controls', []))}."
    ))


def _holdout(campaigns, level):
    body = []
    if level == "medium":
        body.append(_paragraph(budget_screening.MEDIUM_HOLDOUT_LEAD))
    body.extend(f"<p><strong>{_escape(heading)}.</strong> {_escape(text)}</p>" for heading, text in SECTIONS)
    body.append("<ul>")
    for campaign in campaigns:
        example = cost_example(campaign["total_spend"], campaign["confidence_interval"])
        body.append(f"<li><strong>{_escape(campaign['campaign_name'])}</strong> — {_escape(example)}</li>")
    body.append("</ul>")
    body.append(_HOLDOUT_CONTROLS)
    return _section(TITLE, "".join(body))


def _data_appendix(report):
    fields = (
        "total_spend", "reported_roas", "true_incremental_roas", "confidence_interval",
        "standard_error", "mde80", "incremental_revenue", "status",
    )
    return _section("Data appendix", "".join((
        "<h3>Campaign statistics</h3>",
        _table("Campaign statistics", ("Campaign", *fields),
               ((campaign["campaign_name"], *(_diagnostic_value(campaign[field]) for field in fields))
                for campaign in report["campaigns"])),
        "<h3>Model diagnostics</h3>",
        _table("Model diagnostics", ("Key", "Value"),
               ((key, _diagnostic_value(value)) for key, value in report["model_diagnostics"].items())),
        "<h3>Inputs</h3>",
        _table("Inputs", ("Key", "File", "SHA256"),
               ((key, source["file"], source["sha256"][:12]) for key, source in report["inputs"].items())),
        "<h3>Dataset summary</h3>",
        _paragraph(_dataset_line(report["dataset"])),
    )))


def render_html_report(report: dict) -> str:
    """Return a complete HTML document containing the original report data."""
    report_id = _escape(report["report_id"])
    engine = report["engine"]
    method, gate = _escape(engine["method"]), _escape(engine["validation_gate"])
    rule = report["decision_rule"]
    campaigns = report["campaigns"]
    assessment = report.get("screening") or budget_screening.not_screened()
    level = assessment["risk_level"]

    parts = [f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Ad attribution audit — Report {report_id}</title>
<style>{_STYLES}</style>
</head>
<body>
<main>
<header>
<p class="brand">AD ATTRIBUTION AUDITOR</p>
<h1>Ad attribution audit</h1>
<p class="report-id">Report {report_id}</p>
<p>{_escape(_dataset_line(report['dataset']))}<br>
Method: {method} (model status: {_escape(engine['model_status'])}).<br>
Prepared {_escape(report['created_utc'][:10])}</p>
</header>
"""]
    if level == "high":
        parts.append(f'<p class="high-risk"><strong>{_escape(budget_screening.HIGH_WARNING)}</strong></p>')
    parts.append(_headline(report["store"], level))

    margin_pct = min(90, max(10, round(rule["contribution_margin"] * 100)))
    margin_controls = _MARGIN_CONTROLS.format(pct=margin_pct, threshold=_x(rule["break_even_iroas"]))
    if level == "high":
        margin_controls += _paragraph(
            "High endogeneity risk: at this screening level, actions other than kill stay at "
            "hold at any margin, and positive labels remain downgraded."
        )
    parts.append(_section("Decision threshold", _paragraph(rule["rule"]) + margin_controls))
    parts.append(_screening(assessment, level))

    results = _paragraph(rule.get("action_notice", ACTION_NOTICE)) + _table(
        "Per-campaign results", ("Platform", "Campaign", "Spend", "Platform ROAS", "Est. iROAS", "95% CI",
                                 "Label", "MDE80", "Action"),
        (_campaign_row(campaign, level) for campaign in campaigns),
    )
    if engine["validation_gate"] != "PASS":
        results += (f"<p><strong>Validation hold.</strong> The engine's validation gate is <code>{gate}</code> "
                    "(validation/v2-calibration-2026-11-09.md). Maintain all current budgets while gathering "
                    "evidence on the provisional priorities above.</p>")
    parts.append(_section("Per-campaign results", results))
    parts.append('<section id="campaign-explorer"><h2>Campaign explorer</h2>'
                 '<div class="filters" role="group" aria-label="Filter by platform"></div>'
                 '<div class="cards"></div></section>')

    parts.extend((
        _inconclusive(campaigns, rule["practical_zero_delta"]),
        _warnings(report["warnings"]),
        _diagnostics(report["model_diagnostics"]),
    ))
    if report.get("legacy_health_alerts"):
        parts.append(_section(
            "Legacy dashboard alerts (not campaign inference)",
            _paragraph(report["legacy_health_alerts_note"])
            + _list(f"{alert['severity']}: {alert['title']} — {alert['message']}"
                    for alert in report["legacy_health_alerts"]),
        ))
    parts.extend((
        _paragraph(f"MDE80: {report['mde80_definition']}"),
        _holdout(campaigns, level),
        _data_appendix(report),
        f'<footer>Report {report_id} · {method} · Validation gate: {gate}</footer>',
        "</main>",
    ))
    # Keep HTML's script parser in its initial state and preserve strings on JSON decode.
    data = json.dumps(report, ensure_ascii=False).replace("</", r"<\/")
    data = data.replace("<!--", r"\u003c!--")
    data = data.replace("http://", r"http:\u002f/").replace("https://", r"https:\u002f/")
    parts.extend((f'<script type="application/json" id="report-data">{data}</script>',
                  f"<script>{_SCRIPT}</script>", "</body>", "</html>"))
    return "\n".join(parts)


def write_html_report(report: dict, path) -> Path:
    """Write the report as UTF-8 and return its path."""
    path = Path(path)
    path.write_text(render_html_report(report), encoding="utf-8")
    return path


_MARGIN_CONTROLS = """<div class="margin-controls">
<label for="margin-slider">Contribution margin <output id="margin-value" for="margin-slider">{pct}%</output></label>
<input type="range" id="margin-slider" min="10" max="90" step="1" value="{pct}">
<p>Break-even iROAS <output id="breakeven-value" for="margin-slider">{threshold}</output></p>
<p id="margin-notice" class="notice" aria-live="polite" hidden></p>
</div>"""

_HOLDOUT_CONTROLS = """<div class="holdout-calculator">
<h3>Holdout calculator</h3>
<p>Opportunity cost = spend paused during the holdout × the campaign's estimated iROAS interval.</p>
<div class="calculator-controls">
<label for="holdout-campaign">Campaign</label>
<select id="holdout-campaign"></select>
<label for="holdout-share">Spend paused <output id="holdout-share-value" for="holdout-share">20%</output></label>
<input type="range" id="holdout-share" min="5" max="50" step="1" value="20">
<label for="holdout-weeks">Duration <output id="holdout-weeks-value" for="holdout-weeks">2 weeks</output></label>
<input type="range" id="holdout-weeks" min="1" max="8" step="1" value="2">
</div>
<div id="holdout-result" aria-live="polite"></div>
</div>"""

_STYLES = """
:root {
  color-scheme: light;
  --ink: #1a2b40;
  --muted: #536374;
  --teal: #0a6366;
  --rule: #d7e0e4;
  --paper: #fcfcfa;
  font-family: system-ui, sans-serif;
  color: var(--ink);
  background: var(--paper);
}
* { box-sizing: border-box; }
[hidden] { display: none; }
body { margin: 0; font-size: 1rem; line-height: 1.6; }
main { max-width: 55rem; margin: 0 auto; padding: 3.5rem clamp(1rem, 4vw, 2.5rem); }
header { padding-bottom: 2rem; }
section { padding: 2rem 0; border-top: 1px solid var(--rule); }
h1, h2, h3 { font-family: Georgia, "Times New Roman", serif; font-weight: 400; line-height: 1.15; }
h1 { font-size: clamp(2.6rem, 8vw, 4.5rem); margin: .3em 0 .2em; }
h2 { font-size: clamp(1.65rem, 4vw, 2.2rem); margin: 0 0 .8em; }
h3 { font-size: 1.35rem; margin: 1em 0 .45em; }
p, ul { margin: .65rem 0; }
ul { padding-left: 1.35rem; }
li + li { margin-top: .25rem; }
.brand, .badge, .platform { letter-spacing: .08em; text-transform: uppercase; }
.brand, .platform { color: var(--teal); font-size: .75rem; font-weight: 700; }
.report-id, header > p:last-child, footer { color: var(--muted); }
.high-risk, .notice { padding: .75rem 1rem; border-left: 3px solid var(--teal); background: #eef4f3; }
.high-risk { border-color: #a4751a; background: #fff2d6; margin: 0 0 2rem; }
.figures {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 1rem 1.75rem;
  margin: 0 0 1.25rem;
}
.figures > div { border-bottom: 1px solid var(--rule); padding: 0 0 1rem; }
.figures dt { color: var(--muted); font-size: .9rem; }
.figures dd { margin: 0; }
.figures strong {
  display: block;
  font-size: clamp(1.5rem, 5vw, 2.4rem);
  font-weight: 550;
  font-variant-numeric: tabular-nums;
  line-height: 1.3;
}
.figures span { display: block; margin-top: .25rem; font-size: .85rem; }
.table-scroll, .chart-scroll { overflow-x: auto; }
table { width: 100%; border-collapse: collapse; text-align: left; font-size: .84rem; }
th, td { padding: .5rem .55rem; border-bottom: 1px solid var(--rule); vertical-align: top; }
th { font-weight: 650; }
td { font-variant-numeric: tabular-nums; overflow-wrap: anywhere; }
td:first-child, th:first-child { padding-left: 0; }
td:last-child, th:last-child { padding-right: 0; }
.margin-controls, .calculator-controls { max-width: 36rem; margin: 1rem 0; }
label { display: block; font-weight: 600; }
input[type="range"] { width: 100%; margin: .35rem 0; accent-color: var(--teal); }
output { color: var(--teal); font-weight: 650; font-variant-numeric: tabular-nums; }
select { width: 100%; margin: .35rem 0 .75rem; padding: .35rem; font: inherit; color: inherit; }
button { font: inherit; cursor: pointer; color: var(--teal); }
:focus-visible { outline: 2px solid var(--teal); outline-offset: 3px; }
.filters { display: flex; flex-wrap: wrap; gap: .55rem; margin-bottom: 1rem; }
.filter-btn {
  border: 1px solid var(--rule);
  border-radius: 1rem;
  padding: .25rem .8rem;
  background: transparent;
  font-size: .85rem;
}
.filter-btn[aria-pressed="true"] { background: var(--teal); border-color: var(--teal); color: white; }
.campaign-card { border-top: 1px solid var(--rule); padding: 1rem 0; }
.campaign-card h3 { margin: 0; overflow-wrap: anywhere; }
.badges { display: flex; flex-wrap: wrap; align-items: center; gap: .5rem; }
.badge { border-radius: 1rem; padding: .15rem .55rem; font-size: .69rem; font-weight: 700; background: #eaedf0; }
.action-badge[data-action="keep"] { color: #075456; background: #def0ed; }
.action-badge[data-action="kill"] { color: #7b252c; background: #f4e3e5; }
.action-badge[data-action="hold"] { color: #4c4e50; background: #ebe9e4; }
.action-badge.changed { outline: 2px solid var(--teal); outline-offset: 1px; }
.campaign-stats { font-size: .88rem; font-variant-numeric: tabular-nums; }
.reason-toggle { border: 0; background: none; padding: 0; text-decoration: underline; text-underline-offset: .2em; }
.reason-panel { padding: .5rem 0 0; }
.chart-scroll { margin: .65rem 0; }
svg { display: block; width: 100%; }
.headline-svg { min-width: 33rem; }
.whisker-svg { min-width: 16rem; }
svg text { fill: var(--ink); font: 13px system-ui, sans-serif; font-variant-numeric: tabular-nums; }
.row-title { font-weight: 650; }
svg line { vector-effect: non-scaling-stroke; }
.axis { stroke: var(--rule); }
.zero-line { stroke: #788695; stroke-dasharray: 3 3; }
.whisker line { stroke: var(--ink); stroke-width: 1.5; }
.headline-whisker line { stroke: #357f82; stroke-width: 2; }
.estimate-dot, .estimate-bar { fill: var(--ink); }
.reported-bar { fill: #b5c3ca; }
.breakeven-marker { stroke: var(--teal); stroke-width: 2; }
.legend { display: flex; flex-wrap: wrap; gap: .4rem 1.2rem; padding: 0; list-style: none; font-size: .83rem; }
.legend li { display: flex; align-items: center; gap: .4rem; margin: 0; }
.legend-key { display: inline-block; width: 1rem; height: .55rem; background: var(--ink); }
.legend-reported { background: #b5c3ca; }
.legend-interval { height: 2px; background: #357f82; }
.holdout-calculator { border-top: 1px solid var(--rule); margin-top: 1.3rem; padding-top: .35rem; }
footer { padding-top: 1.25rem; border-top: 1px solid var(--rule); font-size: .8rem; overflow-wrap: anywhere; }
@media (max-width: 38rem) {
  main { padding-top: 2rem; }
  th { min-width: 5rem; }
  .figures { gap: .8rem 1rem; }
}
@media print {
  :root { background: white; }
  main { max-width: none; padding: 0; }
  #margin-slider, .filters, .calculator-controls, .reason-toggle { display: none; }
  .reason-panel[hidden], .reason[hidden], .campaign-card[hidden] { display: block; }
  .campaign-card { break-inside: avoid; page-break-inside: avoid; }
  .table-scroll, .chart-scroll { overflow: visible; }
  .headline-svg, .whisker-svg { min-width: 0; }
  th { min-width: 0; overflow-wrap: anywhere; }
}
"""

_SCRIPT = r"""
const REPORT = JSON.parse(document.getElementById('report-data').textContent);

// === BEGIN PORTED RULES ===
const DOWNGRADE_PHRASE = "indistinguishable from demand-following spend";

const floatBits = new DataView(new ArrayBuffer(8));

function formatFixed(v, digits) {
  if (Number.isNaN(v)) return "nan";
  if (!Number.isFinite(v)) return v < 0 ? "-inf" : "inf";

  // Work with the exact binary significand and a power-of-two denominator.
  // Scaling a Number first would round a second time before resolving ties.
  floatBits.setFloat64(0, v);
  const bits = floatBits.getBigUint64(0);
  const negative = (bits >> 63n) !== 0n;
  const exponent = Number((bits >> 52n) & 0x7ffn);
  const fraction = bits & ((1n << 52n) - 1n);
  const significand = exponent === 0 ? fraction : fraction | (1n << 52n);
  const shift = (exponent || 1) - 1075;

  let rounded = significand * (10n ** BigInt(digits));
  if (shift >= 0) {
    rounded <<= BigInt(shift);
  } else {
    const divisor = 1n << BigInt(-shift);
    const remainder = rounded % divisor;
    rounded /= divisor;
    if (remainder * 2n > divisor || (remainder * 2n === divisor && rounded % 2n === 1n)) {
      rounded += 1n;
    }
  }

  const sign = negative ? "-" : "";
  if (digits === 0) return sign + rounded.toString();
  const value = rounded.toString().padStart(digits + 1, "0");
  return sign + value.slice(0, -digits) + "." + value.slice(-digits);
}

function fmt2(v) {
  return formatFixed(v, 2);
}

function groupThousands(integer) {
  return integer.replace(/\B(?=(\d{3})+(?!\d))/g, ",");
}

function fmt0(v) {
  return groupThousands(formatFixed(v, 0));
}

function classifyEffectInterval(ci) {
  if (!Array.isArray(ci) || ci.length !== 2 || !ci.every(Number.isFinite) || ci[0] > ci[1]) {
    return "unavailable";
  }
  const [lo, hi] = ci;
  if (-0.2 <= lo && hi <= 0.2) return "practically_zero";
  if (lo > 0) return "positive";
  if (hi < 0) return "negative";
  return "inconclusive";
}

function actionForInterval(ci, threshold) {
  if (classifyEffectInterval(ci) === "unavailable") return ["KEEP", "Inference unavailable; hold changes."];
  const margin = fmt2(threshold);
  if (ci[0] > threshold) return ["SCALE", `Entire 95% interval exceeds the ${margin}x margin threshold.`];
  if (ci[1] < threshold) return ["KILL", `Entire 95% interval is below the ${margin}x margin threshold.`];
  return ["KEEP", `95% interval includes the ${margin}x margin threshold.`];
}

function provisionalActionForInterval(ci, threshold) {
  const [action, reason] = actionForInterval(ci, threshold);
  if (action === "SCALE") {
    return ["keep", `The 95% interval's lower bound is above the ${fmt2(threshold)}x break-even. ` +
      "Maintain budget and validate with a holdout before increasing it."];
  }
  if (action === "KILL") return ["kill", reason + " Consider stopping only if a holdout confirms it."];
  return ["hold", reason + " Maintain budget while gathering evidence."];
}

function labelActionNote(ci, threshold) {
  const label = classifyEffectInterval(ci);
  const [action] = provisionalActionForInterval(ci, threshold);
  if (action !== "kill") return "";
  if (label === "inconclusive") {
    return "The label is inconclusive because the interval includes zero — the data cannot establish " +
      "whether this campaign has any effect at all. The kill priority is judged against the " +
      `${fmt2(threshold)}x break-even, not zero: even the most optimistic end of the interval ` +
      `(${fmt2(ci[1])}x) is below break-even, so at every value the data allow, this campaign ` +
      "cannot cover its cost.";
  }
  if (label === "positive") {
    return "The label is positive because the interval excludes zero, but the kill priority is judged " +
      `against the ${fmt2(threshold)}x break-even, not zero: even the most optimistic end of the ` +
      `interval (${fmt2(ci[1])}x) is below break-even, so the effect, though likely real, is too ` +
      "small to cover its cost at this margin.";
  }
  return "";
}

function presentationAction(action, riskLevel) {
  return riskLevel === "high" && action !== "kill" ? "hold" : action;
}

function displayLabel(label, riskLevel) {
  const text = label.replace(/_/g, " ");
  return riskLevel === "high" && label === "positive" ? `${text} (downgraded: ${DOWNGRADE_PHRASE})` : text;
}

function holdoutPausedSpend(spend, sharePct, weeks, windowDays) {
  if (spend === null || spend <= 0) return null;
  const weekly = spend / (windowDays / 7);
  return weekly * weeks * (sharePct / 100);
}

function holdoutCost(spend, ci, sharePct, weeks, windowDays) {
  if (ci === null) return null;
  const paused = holdoutPausedSpend(spend, sharePct, weeks, windowDays);
  return paused === null ? null : [paused * ci[0], paused * ci[1]];
}
// === END PORTED RULES ===

const {campaigns, dataset, decision_rule: rule} = REPORT;
const riskLevel = REPORT.screening?.risk_level ?? null;
const byId = id => document.getElementById(id);
const fmtX = value => value === null ? "n/a" : `${fmt2(value)}x`;
const fmtCI = ci => ci?.length ? `[${fmt2(ci[0])}, ${fmt2(ci[1])}]x` : "unavailable";
const fmtMoney = value => value === null ? "n/a" : "$" + fmt0(value);

function fmtMoney2(value) {
  const [integer, fraction] = fmt2(value).split(".");
  return `$${groupThousands(integer)}.${fraction}`;
}

function element(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function svgElement(tag, attributes, text) {
  const node = document.createElementNS("http" + "://www.w3.org/2000/svg", tag);
  for (const [key, value] of Object.entries(attributes)) node.setAttribute(key, value);
  if (text !== undefined) node.textContent = text;
  return node;
}

function chart(width, height, className, description) {
  const svg = svgElement("svg", {viewBox: `0 0 ${width} ${height}`, class: className, role: "img",
    "aria-label": description});
  const wrapper = element("div", "chart-scroll");
  wrapper.append(svg);
  return {svg, wrapper};
}

function line(group, x1, y1, x2, y2, className) {
  const node = svgElement("line", {x1, y1, x2, y2, class: className});
  group.append(node);
  return node;
}

function plotExtent(scopes, includeReported) {
  let min = 0;
  let max = includeReported ? 0 : -Infinity;
  for (const scope of scopes) {
    const ci = scope.confidence_interval ?? [];
    const values = [scope.true_incremental_roas, ...ci];
    if (includeReported) values.push(scope.reported_roas);
    for (const value of values) {
      if (!Number.isFinite(value)) continue;
      min = Math.min(min, value);
      max = Math.max(max, value);
    }
  }
  if (max === -Infinity) max = 0;
  const pad = (max - min) * 0.05 || 1;
  return [min - pad, max + pad];
}

function plotPosition([min, max], left, right) {
  return value => {
    const clamped = Math.min(max, Math.max(min, value));
    return left + (clamped - min) / (max - min) * (right - left);
  };
}

function addWhisker(parent, ci, x, y, className) {
  if (classifyEffectInterval(ci) === "unavailable") return;
  const [lo, hi] = ci.map(x);
  const group = svgElement("g", {class: className});
  line(group, lo, y, hi, y, "");
  line(group, lo, y - 5, lo, y + 5, "");
  line(group, hi, y - 5, hi, y + 5, "");
  parent.append(group);
}

function buildHeadline() {
  const scopes = [REPORT.store, ...campaigns];
  const rowHeight = 72;
  const width = 760;
  const height = scopes.length * rowHeight;
  const {svg, wrapper} = chart(width, height, "headline-svg", "Platform-reported and estimated ROAS by scope");
  const x = plotPosition(plotExtent(scopes, true), 68, width - 68);
  const zero = x(0);

  function addBar(row, value, y, className) {
    if (!Number.isFinite(value)) {
      row.append(svgElement("text", {x: zero + 6, y: y + 10}, "n/a"));
      return;
    }
    const end = x(value);
    row.append(svgElement("rect", {x: Math.min(zero, end), y, width: Math.abs(end - zero), height: 12,
      class: className}));
    row.append(svgElement("text", {x: value < 0 ? end - 6 : end + 6, y: y + 10,
      "text-anchor": value < 0 ? "end" : "start"}, fmtX(value)));
  }

  scopes.forEach((scope, index) => {
    const row = svgElement("g", {transform: `translate(0 ${index * rowHeight})`});
    row.append(svgElement("text", {x: 0, y: 15, class: "row-title"}, scope.campaign_name ?? "Combined store"));
    line(row, zero, 21, zero, 63, "zero-line");
    addBar(row, scope.reported_roas, 26, "reported-bar");
    addBar(row, scope.true_incremental_roas, 46, "estimate-bar");
    addWhisker(row, scope.confidence_interval, x, 52, "headline-whisker");
    svg.append(row);
  });

  const legend = element("ul", "legend");
  for (const [name, style] of [["Platform-reported ROAS", "reported"],
    ["Estimated iROAS", "estimate"], ["95% CI", "interval"]]) {
    const item = element("li");
    const key = element("span", `legend-key legend-${style}`);
    key.setAttribute("aria-hidden", "true");
    item.append(key, name);
    legend.append(item);
  }
  byId("headline-chart").append(legend, wrapper);
}

function platformName(platform) {
  if (platform === "meta") return "Meta";
  if (platform === "google_ads") return "Google Ads";
  return platform;
}

function buildExplorer() {
  const explorer = byId("campaign-explorer");
  const cards = explorer.querySelector(".cards");
  const width = 720;
  const x = plotPosition(plotExtent(campaigns, false), 10, width - 10);
  const cardViews = campaigns.map((campaign, index) => {
    const {campaign_name: name, platform, confidence_interval: ci, true_incremental_roas: estimate} = campaign;
    const card = element("article", "campaign-card");
    card.dataset.campaign = name;
    card.dataset.platform = platform;
    const badges = element("p", "badges");
    const actionBadge = element("span", "badge action-badge");
    badges.append(element("span", "platform", platformName(platform)),
      element("span", "badge label-badge", displayLabel(campaign.effect_label, riskLevel)), actionBadge);
    const stats = element("p", "campaign-stats",
      `Spend ${fmtMoney(campaign.total_spend)} · Platform ROAS ${fmtX(campaign.reported_roas)} · ` +
      `Est. iROAS ${fmtX(estimate)} · 95% CI ${fmtCI(ci)} · MDE80 ${fmtX(campaign.mde80)}`);

    const {svg, wrapper} = chart(width, 40, "whisker-svg", `${name} iROAS interval and break-even`);
    line(svg, x(-Infinity), 20, x(Infinity), 20, "axis");
    line(svg, x(0), 7, x(0), 33, "zero-line");
    const marker = line(svg, 0, 5, 0, 35, "breakeven-marker");
    marker.append(svgElement("title", {}, "Break-even iROAS"));
    addWhisker(svg, ci, x, 20, "whisker");
    if (Number.isFinite(estimate)) {
      svg.append(svgElement("circle", {cx: x(estimate), cy: 20, r: 4, class: "estimate-dot"}));
    }

    const toggle = element("button", "reason-toggle", "Why this priority");
    toggle.type = "button";
    const details = element("div", "reason-panel");
    details.id = `campaign-reason-${index}`;
    details.hidden = true;
    toggle.setAttribute("aria-controls", details.id);
    toggle.setAttribute("aria-expanded", "false");
    toggle.addEventListener("click", () => {
      details.hidden = !details.hidden;
      toggle.setAttribute("aria-expanded", String(!details.hidden));
    });
    const reason = element("div", "reason");
    details.append(reason);
    const warnings = REPORT.warnings.campaign?.[name];
    if (Array.isArray(warnings) && warnings.length) {
      const list = element("ul");
      for (const warning of warnings) list.append(element("li", "", warning));
      details.append(list);
    }
    card.append(element("h3", "", name), badges, stats, wrapper, toggle, details);
    cards.append(card);

    const [reportAction] = provisionalActionForInterval(ci, rule.break_even_iroas);
    return {card, ci, actionBadge, reason, marker, baseline: presentationAction(reportAction, riskLevel)};
  });

  const platforms = [null, ...new Set(campaigns.map(campaign => campaign.platform))];
  const filters = explorer.querySelector(".filters");
  for (const platform of platforms) {
    const button = element("button", "filter-btn", platform === null ? "All" : platformName(platform));
    button.type = "button";
    button.dataset.platform = platform ?? "";
    button.setAttribute("aria-pressed", String(platform === null));
    button.addEventListener("click", () => {
      for (const sibling of filters.children) sibling.setAttribute("aria-pressed", String(sibling === button));
      for (const {card} of cardViews) card.hidden = platform !== null && card.dataset.platform !== platform;
    });
    filters.append(button);
  }
  return {cardViews, x};
}

function setupMargin({cardViews, x}) {
  const slider = byId("margin-slider");
  const value = byId("margin-value");
  const breakEven = byId("breakeven-value");
  const notice = byId("margin-notice");
  const reportPct = fmt0(rule.contribution_margin * 100);
  const reportThreshold = fmtX(rule.break_even_iroas);

  function update() {
    const pct = slider.valueAsNumber;
    const margin = pct / 100;
    const threshold = 1 / margin;
    value.textContent = `${pct}%`;
    breakEven.textContent = fmtX(threshold);
    notice.hidden = margin === rule.contribution_margin;
    notice.textContent = notice.hidden ? "" :
      `Recomputed at your margin of ${pct}% — the report's stated assumption is ${reportPct}% ` +
      `(break-even ${reportThreshold}). Actions below are re-derived ` +
      "by the same rule; the estimates themselves do not change.";

    for (const {ci, actionBadge, reason, marker, baseline} of cardViews) {
      const [action, baseReason] = provisionalActionForInterval(ci, threshold);
      const presented = presentationAction(action, riskLevel);
      const note = labelActionNote(ci, threshold);
      actionBadge.dataset.action = presented;
      actionBadge.textContent = `${presented} (provisional)`;
      actionBadge.classList.toggle("changed", presented !== baseline);
      reason.textContent = note ? `${baseReason} ${note}` : baseReason;
      const mark = x(threshold);
      marker.setAttribute("x1", mark);
      marker.setAttribute("x2", mark);
    }
  }
  slider.addEventListener("input", update);
  update();
}

function setupHoldout() {
  const select = byId("holdout-campaign");
  const share = byId("holdout-share");
  const weeks = byId("holdout-weeks");
  const result = byId("holdout-result");
  const unavailable = "A holdout cost estimate is unavailable for this campaign (no interval or no spend).";

  for (const campaign of campaigns) select.append(element("option", "", campaign.campaign_name));
  if (!campaigns.length) {
    for (const control of [select, share, weeks]) control.disabled = true;
  }

  function update() {
    const pct = share.valueAsNumber;
    const duration = weeks.valueAsNumber;
    const weekLabel = duration === 1 ? "week" : "weeks";
    byId("holdout-share-value").textContent = `${pct}%`;
    byId("holdout-weeks-value").textContent = `${duration} ${weekLabel}`;

    const campaign = campaigns[select.selectedIndex];
    const spend = campaign?.total_spend ?? null;
    const ci = campaign?.confidence_interval ?? null;
    const paused = holdoutPausedSpend(spend, pct, duration, dataset.days);
    const cost = holdoutCost(spend, ci, pct, duration, dataset.days);
    if (cost === null) {
      result.textContent = unavailable;
      return;
    }
    const amount = fmtMoney2(paused);
    result.textContent =
      `Pausing ${pct}% of ${campaign.campaign_name} for ${duration} ${weekLabel} withholds about ${amount} ` +
      "of spend (at this report's average weekly rate). Opportunity cost = " +
      `spend paused × iROAS interval = ${amount} × ${fmtCI(ci)} = [${fmtMoney2(cost[0])}, ${fmtMoney2(cost[1])}] ` +
      "in foregone incremental revenue. Planning estimate from the report window " +
      `(${dataset.start} to ${dataset.end}, ${dataset.days} days); in a live test, use the actual withheld spend.`;
  }
  select.addEventListener("change", update);
  share.addEventListener("input", update);
  weeks.addEventListener("input", update);
  update();
}

buildHeadline();
setupMargin(buildExplorer());
setupHoldout();
"""
