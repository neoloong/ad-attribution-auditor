"""Small, deterministic, dependency-free PDF renderer for the Gate 1 sample.

All performance values come from the recorded engine runs. Never replace a
missing confidence interval with a fabricated interval or the synthetic truth.
"""
from __future__ import annotations

from pathlib import Path
import math

from ad_audit.engine.models import classify_effect_interval
from ad_audit.report.holdout import ACTION_NOTICE, SECTIONS, TITLE, cost_example

NAVY = (0.10, 0.17, 0.25)
TEAL = (0.04, 0.39, 0.40)
INK = (0.17, 0.22, 0.28)
MUTED = (0.38, 0.43, 0.48)
LIGHT = (0.94, 0.96, 0.97)
AMBER = (0.96, 0.88, 0.70)
WHITE = (1, 1, 1)


def text_width(s, size):
    # Standard Helvetica AFM advance widths, in thousandths of an em.
    groups = {
        278: " !',.:;Iijl", 355: '"', 556: "#$0123456789?abcdeghnopquvy",
        889: "%", 667: "&ABEKPSVXY", 191: "'", 333: "()frt", 389: "*",
        584: "+<=>~", 333: "-", 278: "./", 1015: "@", 722: "CDHNRU",
        611: "FTZ", 778: "GOQ", 500: "Jksxz", 833: "Mmw", 944: "W",
        278: "[]\\", 469: "^", 556: "_", 333: "`", 334: "{}", 260: "|",
        1000: "—", 556: "–", 350: "•",
    }
    widths = {char: width for width, chars in groups.items() for char in chars}
    return sum(widths.get(char, 556) for char in s) * size / 1000


class PDF:
    width, height = 612, 792

    def __init__(self):
        self.pages = []
        self.ops = []

    def rect(self, x, y, w, h, color):
        self.ops.append(f"{' '.join(map(str, color))} rg {x} {self.height-y-h} {w} {h} re f\n")

    def text(self, x, y, value, size=10, bold=False, color=INK):
        assert 30 <= y <= 757, (y, value)
        assert x + text_width(value, size) <= 579, (x, value)
        escaped = value.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        self.ops.append(f"BT /{'F2' if bold else 'F1'} {size} Tf "
                        f"{' '.join(map(str, color))} rg 1 0 0 1 {x} {self.height-y} Tm ({escaped}) Tj ET\n")

    def paragraph(self, x, y, value, width=528, size=10.5, leading=15, color=INK, bold=False):
        words, line = value.split(), ""
        for word in words:
            candidate = f"{line} {word}".strip()
            # Leave space for slightly larger bold-font advances.
            if text_width(candidate, size) > width * (0.96 if bold else 0.99):
                self.text(x, y, line, size, bold, color)
                y += leading
                line = word
            else:
                line = candidate
        if line:
            self.text(x, y, line, size, bold, color)
        return y + leading

    def page(self, number, title, subtitle):
        if self.ops:
            self.pages.append("".join(self.ops).encode("cp1252"))
        self.ops = []
        self.rect(0, 0, 612, 9, TEAL)
        self.text(42, 39, "AD ATTRIBUTION AUDITOR", 9, True, TEAL)
        self.rect(338, 23, 232, 23, AMBER)
        self.text(351, 38, "SAMPLE — synthetic data", 10, True, NAVY)
        self.text(42, 92, title, 27, True, NAVY)
        self.text(42, 116, subtitle, 10, False, MUTED)
        self.rect(42, 747, 528, 0.6, (0.80, 0.84, 0.87))
        self.text(42, 765-9, "Prepared 2026-11-09  |  Local synthetic demonstration", 8, False, MUTED)
        self.text(539, 756, f"{number} / 4", 8, False, MUTED)

    def save(self, path):
        self.pages.append("".join(self.ops).encode("cp1252"))
        objects = [b"<< /Type /Catalog /Pages 2 0 R >>", b"",
                   b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>",
                   b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>"]
        kids = []
        for content in self.pages:
            page_id = len(objects) + 1
            stream_id = page_id + 1
            kids.append(f"{page_id} 0 R")
            objects.append((f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
                            f"/Resources << /Font << /F1 3 0 R /F2 4 0 R >> >> "
                            f"/Contents {stream_id} 0 R >>").encode())
            objects.append(f"<< /Length {len(content)} >>\nstream\n".encode() + content + b"endstream")
        objects[1] = f"<< /Type /Pages /Kids [{' '.join(kids)}] /Count {len(kids)} >>".encode()
        objects.append(b"<< /Title (SAMPLE - Synthetic Ad Attribution Audit) /Author (Ad Attribution Auditor) >>")
        result = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
        offsets = [0]
        for i, obj in enumerate(objects, 1):
            offsets.append(len(result))
            result.extend(f"{i} 0 obj\n".encode() + obj + b"\nendobj\n")
        xref = len(result)
        result.extend(f"xref\n0 {len(objects)+1}\n0000000000 65535 f \n".encode())
        for offset in offsets[1:]:
            result.extend(f"{offset:010d} 00000 n \n".encode())
        result.extend((f"trailer\n<< /Size {len(objects)+1} /Root 1 0 R /Info {len(objects)} 0 R >>\n"
                       f"startxref\n{xref}\n%%EOF\n").encode())
        Path(path).write_bytes(result)


def dollars(value):
    return "Unavailable" if value is None else f"${value:,.0f}"


def roas(value):
    return "Unavailable" if value is None else f"{value:.4f}x"


def interval(metrics):
    ci = metrics["confidence_interval"]
    return f"[{ci[0]:.4f}, {ci[1]:.4f}]x" if ci else "Unavailable"


def margin_threshold(contribution_margin=None):
    """Return the stated assumption and profit break-even revenue iROAS."""
    margin = 0.40 if contribution_margin is None else float(contribution_margin)
    if not math.isfinite(margin) or not 0 < margin <= 1:
        raise ValueError("Contribution margin must be finite, greater than 0 and at most 1")
    return margin, 1 / margin


def action_for_interval(ci, threshold):
    """Return the original action vocabulary used in validation artifacts."""
    if classify_effect_interval(ci) == "unavailable":
        return "KEEP", "Inference unavailable; hold changes."
    if ci[0] > threshold:
        return "SCALE", f"Entire 95% interval exceeds the {threshold:.2f}x margin threshold."
    if ci[1] < threshold:
        return "KILL", f"Entire 95% interval is below the {threshold:.2f}x margin threshold."
    return "KEEP", f"95% interval includes the {threshold:.2f}x margin threshold."


ACTION_RULE = (
    "Use keep if the entire 95% CI is above break-even, kill if the entire CI is below break-even, "
    "and hold if it includes break-even or is unavailable."
)


def provisional_action_for_interval(ci, threshold):
    action, reason = action_for_interval(ci, threshold)
    if action == "SCALE":
        return "keep", (f"The 95% interval's lower bound is above the {threshold:.2f}x break-even. "
                        "Maintain budget and validate with a holdout before increasing it.")
    if action == "KILL":
        return "kill", reason + " Consider stopping only if a holdout confirms it."
    return "hold", reason + " Maintain budget while gathering evidence."


def render_report(data, path, contribution_margin=None):
    margin, threshold = margin_threshold(contribution_margin)
    doc = PDF()
    combined = data["combined"]
    ir = combined["incremental_roas"]
    runs = data["campaign_results"]
    dates = data["dataset"]
    period = f"{dates['start']} to {dates['end']}  |  Meta + Google Ads  |  Shopify store"
    doc.page(1, "Ad attribution audit", period)
    doc.rect(42, 141, 528, 69, LIGHT)
    doc.text(56, 163, f"SYNTHETIC QUALITY GATE: {data['gate']}", 11, True, TEAL)
    doc.paragraph(56, 183, "Joint campaign estimates with 95% confidence intervals. Suggested actions "
                  "apply to this synthetic example; validate real budget changes with a holdout.", width=495, size=10)
    metrics = [("TOTAL AD SPEND", dollars(ir["total_spend"])),
               ("PLATFORM ROAS", f"{ir['reported_roas']:.4f}x"),
               ("ESTIMATED STORE iROAS", f"{ir['true_incremental_roas']:.4f}x")]
    for i, (label, value) in enumerate(metrics):
        x = 42 + i * 178
        doc.text(x, 244, label, 8, True, MUTED)
        doc.text(x, 276, value, 25, True, NAVY)
    doc.text(42, 316, "Headline findings", 15, True, NAVY)
    y = doc.paragraph(42, 339,
                      f"Store 95% interval: {interval(ir)}. Estimated incremental revenue is "
                      f"{dollars(ir['incremental_revenue'])}, versus {dollars(ir['reported_revenue'])} "
                      f"claimed by platforms. Estimated iROAS is {ir['inflation_rate']:.2%} below platform ROAS.")
    flagged = [r["campaign"] for r in runs
               if classify_effect_interval(r["incremental_roas"]["confidence_interval"])
               in ("practically_zero", "negative")]
    y = doc.paragraph(42, y + 6,
                      f"Practical-zero or negative evidence: {', '.join(flagged) if flagged else 'none'}. "
                      "Intervals crossing zero are inconclusive unless inside +/-0.2x. "
                      "Negative estimates and interval bounds are retained.")
    doc.text(42, y + 24, "Reported versus estimated returns", 15, True, NAVY)
    top = y + 39
    xs = [42, 182, 252, 324, 396]
    doc.rect(42, top, 528, 36, NAVY)
    headers = [("Scope",), ("Spend",), ("Platform", "ROAS"), ("Estimated", "iROAS"), ("95% confidence", "interval")]
    for x, parts in zip(xs, headers):
        for j, label in enumerate(parts):
            doc.text(x + 8, top + 14 + j * 12, label, 9, True, WHITE)
    entries = [("Combined store", ir)] + [(r["campaign"], r["incremental_roas"]) for r in runs]
    for i, (name, metrics) in enumerate(entries):
        row_top = top + 36 + i * 37
        doc.rect(42, row_top, 528, 37, LIGHT if i % 2 == 0 else WHITE)
        values = [name, dollars(metrics["total_spend"]), roas(metrics["reported_roas"]),
                  roas(metrics["true_incremental_roas"]), interval(metrics)]
        for x, value in zip(xs, values):
            doc.text(x + 8, row_top + 23, value, 8.5, i == 0, INK)
    note_y = top + 36 + 4 * 37 + 19
    doc.paragraph(42, note_y,
                  "All campaign effects come from one daily revenue regression. Campaign contributions "
                  "sum to the store estimate. Intervals are marginal 95% HC3 intervals, conditional on "
                  "observed spend, and do not establish real-world causality.", size=9, leading=13, color=MUTED)

    doc.page(2, "Campaign action list", "keep / kill / hold")
    margin_note = ("Assumed" if contribution_margin is None else "Customer-supplied")
    rule = (f"{margin_note} contribution margin: {margin:.0%}. Break-even iROAS = 1/margin = "
            f"{threshold:.2f}x. {ACTION_RULE}")
    y = doc.paragraph(42, 145, rule, size=10.5, leading=15)
    doc.paragraph(42, y + 5, ACTION_NOTICE, size=10.5, leading=15)
    for i, r in enumerate(runs):
        top = 240 + i * 150
        doc.rect(42, top, 528, 133, LIGHT)
        doc.text(56, top + 25, r["campaign"], 15, True, NAVY)
        doc.rect(440, top + 10, 114, 24, TEAL)
        metrics = r["incremental_roas"]
        proposed_action, reason = provisional_action_for_interval(metrics["confidence_interval"], threshold)
        action = proposed_action if data["gate"] == "PASS" else "hold"
        doc.text(451, top + 26, f"{action} (provisional)", 10, True, WHITE)
        doc.text(56, top + 49,
                 f"Platform {roas(metrics['reported_roas'])}  |  Estimate {roas(metrics['true_incremental_roas'])}"
                 f"  |  95% CI {interval(metrics)}", 9)
        label = classify_effect_interval(metrics["confidence_interval"]).replace("_", " ")
        doc.text(56, top + 68, f"Evidence label: {label} (practical region +/-0.2x).", 9, False, MUTED)
        if data["gate"] != "PASS":
            reason = f"Validation hold. Provisional priority: {proposed_action}. {reason}"
        doc.paragraph(56, top + 92, reason, width=491, size=10, leading=14)

    doc.page(3, "Methodology & limitations", "Aggregate daily analysis  |  Revenue return, not contribution profit")
    doc.text(42, 157, "How the engine produced these figures", 15, True, NAVY)
    model = combined["campaign_model"]
    sections = [
        ("Inputs and model",
         f"One joint OLS model uses {model['n_obs']} daily Shopify revenue observations, an intercept, "
         "each campaign's daily spend, day-of-week indicators, and a normalized elapsed-day trend. "
         "Revenue dollars per spend dollar give campaign iROAS directly. Platform claims and order "
         "UTMs do not supply causal labels. GSC is used only for overlap diagnostics."),
        ("Calendar controls and baseline",
         "The campaign model uses weekly effects and linear trend; short-window month effects are "
         "excluded. Organic demand is the model prediction with all campaign spend set to zero on "
         "each observed date. Separate effects require enough independent spend variation. "
         "Unidentified campaigns return no point estimate or interval."),
        ("Uncertainty and signed estimates",
         "Two-sided 95% intervals use HC3 heteroskedasticity-robust OLS standard errors and "
         "Student t(n-p) critical values. Combined uncertainty includes cross-campaign covariance. "
         "Negative effects and bounds remain negative. Evidence labels are positive, negative, "
         "practically zero (CI inside +/-0.2x), inconclusive, or unavailable."),
        ("Causal and financial limitations",
         "HC3 does not correct serial correlation or endogenous spend. Promotions, omitted channels, "
         "nonlinear seasonality, carryover, saturation and interactions can bias estimates. Missing "
         "campaign-date rows are treated as zero spend; missing interior Shopify days disable campaign "
         f"inference. Contribution margin {margin:.0%} implies break-even iROAS {threshold:.2f}x."),
        ("Validation scope",
         "Validation v2 supersedes the five-seed Gate-1 PASS. Calibration and stress results are in "
         "validation/v2-calibration-2026-11-09.md. These displayed estimates use the original synthetic "
         "fixture; they do not establish calibration with endogenous spend, serial correlation or "
         "carryover. Validate material budget changes with a controlled holdout."),
    ]
    y = 185
    for title, body in sections:
        doc.text(42, y, title, 11, True, TEAL)
        y = doc.paragraph(42, y + 21, body, size=10.5, leading=15) + 18

    doc.page(4, TITLE, "")
    y = 130
    for title, body in SECTIONS:
        doc.text(42, y, title, 11, True, TEAL)
        y = doc.paragraph(42, y + 16, body, size=10, leading=13) + 9
    for run in runs:
        metrics = run["incremental_roas"]
        example = cost_example(metrics["total_spend"], metrics["confidence_interval"])
        y = doc.paragraph(42, y, f"{run['campaign']} — {example}", size=9.5, leading=13) + 4
    doc.save(path)
