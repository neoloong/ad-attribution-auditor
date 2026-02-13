"""Plotly chart builders for the audit dashboard."""

from __future__ import annotations

import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd

from ad_audit.engine.models import AuditResult


def reported_vs_true_roas_bar(result: AuditResult) -> go.Figure:
    """Grouped bar: Reported ROAS vs True Incremental ROAS."""
    ir = result.incremental_roas
    fig = go.Figure(
        data=[
            go.Bar(
                name="Reported ROAS",
                x=["ROAS"],
                y=[ir.reported_roas],
                marker_color="#636EFA",
            ),
            go.Bar(
                name="True Incremental ROAS",
                x=["ROAS"],
                y=[ir.true_incremental_roas],
                marker_color="#EF553B",
            ),
        ]
    )
    fig.update_layout(
        title="Reported vs True Incremental ROAS",
        barmode="group",
        yaxis_title="ROAS",
        template="plotly_white",
        height=400,
    )
    return fig


def spend_vs_conversions_dual_axis(result: AuditResult) -> go.Figure:
    """Dual-axis time series: daily spend (bars) vs actual conversions (line)."""
    df = result.daily_df
    if df is None or df.empty:
        return go.Figure()

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    fig.add_trace(
        go.Bar(
            x=df["date"],
            y=df["spend"],
            name="Ad Spend ($)",
            marker_color="rgba(99, 110, 250, 0.6)",
        ),
        secondary_y=False,
    )

    fig.add_trace(
        go.Scatter(
            x=df["date"],
            y=df["actual_conversions"],
            name="Actual Conversions",
            mode="lines+markers",
            line=dict(color="#EF553B", width=2),
        ),
        secondary_y=True,
    )

    fig.update_layout(
        title="Daily Ad Spend vs Actual Conversions",
        template="plotly_white",
        height=450,
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
    )
    fig.update_yaxes(title_text="Spend ($)", secondary_y=False)
    fig.update_yaxes(title_text="Conversions", secondary_y=True)

    return fig


def revenue_waterfall(result: AuditResult) -> go.Figure:
    """Waterfall: Reported Revenue → Duplicated → Cannibalized → True Incremental."""
    ir = result.incremental_roas
    dup_rev = ir.reported_revenue - ir.reported_revenue * (1 - result.deduplication.duplication_rate)
    cannibal_rev = ir.reported_revenue * result.cannibalization.cannibalized_revenue_fraction

    fig = go.Figure(
        go.Waterfall(
            name="Revenue Breakdown",
            orientation="v",
            x=["Reported Revenue", "Duplicated", "Cannibalized", "True Incremental"],
            y=[
                ir.reported_revenue,
                -dup_rev,
                -cannibal_rev,
                0,  # total placeholder
            ],
            measure=["absolute", "relative", "relative", "total"],
            textposition="outside",
            text=[
                f"${ir.reported_revenue:,.0f}",
                f"-${dup_rev:,.0f}",
                f"-${cannibal_rev:,.0f}",
                f"${ir.incremental_revenue:,.0f}",
            ],
            connector_line_color="rgba(0,0,0,0.3)",
        )
    )
    fig.update_layout(
        title="Revenue Attribution Waterfall",
        template="plotly_white",
        height=450,
        showlegend=False,
    )
    return fig


def attribution_breakdown_pie(result: AuditResult) -> go.Figure:
    """Donut chart: Truly Incremental vs Cannibalized vs Duplicated."""
    ir = result.incremental_roas
    dup_rev = ir.reported_revenue * result.deduplication.duplication_rate
    cannibal_rev = ir.reported_revenue * result.cannibalization.cannibalized_revenue_fraction
    incremental = max(0, ir.reported_revenue - dup_rev - cannibal_rev)

    labels = ["Truly Incremental", "Cannibalized", "Duplicated"]
    values = [incremental, cannibal_rev, dup_rev]

    fig = go.Figure(
        data=[
            go.Pie(
                labels=labels,
                values=values,
                hole=0.45,
                marker_colors=["#00CC96", "#FFA15A", "#EF553B"],
            )
        ]
    )
    fig.update_layout(
        title="Attribution Breakdown",
        template="plotly_white",
        height=400,
    )
    return fig


def brand_search_overlap_chart(result: AuditResult) -> go.Figure:
    """Dual-axis: ad platform reported conversions vs brand search clicks over time."""
    df = result.daily_df
    if df is None or df.empty or "brand_clicks" not in df.columns:
        return go.Figure()

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    fig.add_trace(
        go.Scatter(
            x=df["date"],
            y=df["reported_conversions"],
            name="Ad Platform Reported Conversions",
            mode="lines",
            line=dict(color="#636EFA", width=2),
        ),
        secondary_y=False,
    )
    fig.add_trace(
        go.Scatter(
            x=df["date"],
            y=df["brand_clicks"],
            name="Brand Search Clicks",
            mode="lines",
            line=dict(color="#00CC96", width=2),
        ),
        secondary_y=True,
    )

    fig.update_layout(
        title="Ad Platform Conversions vs Brand Search Clicks",
        template="plotly_white",
        height=400,
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
    )
    fig.update_yaxes(title_text="Reported Conversions", secondary_y=False)
    fig.update_yaxes(title_text="Brand Clicks", secondary_y=True)
    return fig
