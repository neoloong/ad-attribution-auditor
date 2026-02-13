"""Standalone HTML report generation with embedded Plotly charts."""

from __future__ import annotations

from pathlib import Path

from jinja2 import Template

from ad_audit.engine.models import AuditResult, AuditMode
from ad_audit.visualization.charts import (
    reported_vs_true_roas_bar,
    spend_vs_conversions_dual_axis,
    revenue_waterfall,
    attribution_breakdown_pie,
    brand_search_overlap_chart,
)

TEMPLATE_PATH = Path(__file__).parent / "templates" / "report_base.html"


def export_html_report(
    result: AuditResult,
    ai_summary: str = "",
) -> str:
    """Render a self-contained HTML report string."""
    template_text = TEMPLATE_PATH.read_text(encoding="utf-8")
    template = Template(template_text)

    s = result.summary_dict
    ir = result.incremental_roas

    # Build Plotly chart HTML snippets (fully embedded, no external deps)
    charts = []
    for chart_fn in [
        reported_vs_true_roas_bar,
        attribution_breakdown_pie,
    ]:
        fig = chart_fn(result)
        charts.append(fig.to_html(full_html=False, include_plotlyjs=False))

    if result.mode == AuditMode.AGGREGATE and result.daily_df is not None:
        for chart_fn in [
            spend_vs_conversions_dual_axis,
            revenue_waterfall,
            brand_search_overlap_chart,
        ]:
            fig = chart_fn(result)
            if fig.data:
                charts.append(fig.to_html(full_html=False, include_plotlyjs=False))

    # Findings bullets
    findings = [
        f"Audit mode: {s['mode']}",
        f"The ad platform's reported ROAS ({ir.reported_roas:.2f}x) is inflated by {ir.inflation_rate:.0%} "
        f"compared to the true incremental ROAS ({ir.true_incremental_roas:.2f}x).",
        f"Duplication rate: {result.deduplication.duplication_rate:.1%} of platform-reported conversions "
        f"exceed actual e-commerce orders.",
        f"Cannibalization score: {result.cannibalization.cannibalization_score:.1%} — "
        f"fraction of spend-on days where ad platform claims overlap with organic brand search intent.",
    ]

    if result.total_matched_orders > 0:
        findings.append(
            f"User-level: {result.truly_incremental_orders} of {result.total_matched_orders} "
            f"matched orders are truly incremental ({result.cannibalized_orders} cannibalized)."
        )

    html = template.render(
        reported_roas=f"{ir.reported_roas:.2f}",
        true_roas=f"{ir.true_incremental_roas:.2f}",
        inflation_rate=f"{ir.inflation_rate:.0%}",
        duplication_rate=f"{result.deduplication.duplication_rate:.1%}",
        cannibalization_score=f"{result.cannibalization.cannibalization_score:.1%}",
        correlation=f"{s['correlation_mean']:.2f}",
        total_spend=f"{ir.total_spend:,.0f}",
        reported_revenue=f"{ir.reported_revenue:,.0f}",
        incremental_revenue=f"{ir.incremental_revenue:,.0f}",
        charts=charts,
        ai_summary=ai_summary,
        findings=findings,
    )

    return html
