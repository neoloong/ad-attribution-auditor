"""Trend charts: rolling metrics over time for the audit dashboard."""

from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from ad_audit.engine.models import AuditResult


def rolling_duplication_rate_chart(result: AuditResult, window: int = 7) -> go.Figure:
    """Rolling duplication rate over time (reported vs actual conversions)."""
    df = result.daily_df
    if df is None or df.empty:
        return go.Figure()

    rolling_reported = df["reported_conversions"].rolling(window, min_periods=1).sum()
    rolling_actual = df["actual_conversions"].rolling(window, min_periods=1).sum()

    with np.errstate(divide="ignore", invalid="ignore"):
        excess = np.maximum(0, rolling_reported - rolling_actual)
        rolling_dup = np.where(rolling_reported > 0, excess / rolling_reported, 0)

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df["date"], y=rolling_dup,
        mode="lines",
        name=f"Duplication Rate ({window}-day rolling)",
        line=dict(color="#EF553B", width=2),
        fill="tozeroy",
        fillcolor="rgba(239, 85, 59, 0.15)",
    ))

    fig.update_layout(
        title=f"Duplication Rate Trend ({window}-Day Rolling)",
        yaxis_title="Duplication Rate",
        yaxis_tickformat=".0%",
        template="plotly_white",
        height=350,
    )
    return fig


def rolling_roas_comparison_chart(result: AuditResult, window: int = 7) -> go.Figure:
    """Rolling reported ROAS vs estimated true ROAS over time."""
    df = result.daily_df
    if df is None or df.empty:
        return go.Figure()

    rolling_spend = df["spend"].rolling(window, min_periods=1).sum()
    rolling_reported_rev = df["reported_revenue"].rolling(window, min_periods=1).sum()
    rolling_actual_rev = df["actual_revenue"].rolling(window, min_periods=1).sum()

    with np.errstate(divide="ignore", invalid="ignore"):
        reported_roas = np.where(rolling_spend > 0, rolling_reported_rev / rolling_spend, 0)
        actual_roas = np.where(rolling_spend > 0, rolling_actual_rev / rolling_spend, 0)

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df["date"], y=reported_roas,
        mode="lines",
        name="Reported ROAS",
        line=dict(color="#636EFA", width=2),
    ))
    fig.add_trace(go.Scatter(
        x=df["date"], y=actual_roas,
        mode="lines",
        name="Actual ROAS",
        line=dict(color="#00CC96", width=2),
    ))

    # Shade the gap (inflation)
    fig.add_trace(go.Scatter(
        x=pd.concat([df["date"], df["date"][::-1]]),
        y=np.concatenate([reported_roas, actual_roas[::-1]]),
        fill="toself",
        fillcolor="rgba(239, 85, 59, 0.1)",
        line=dict(width=0),
        name="Inflation Gap",
        showlegend=True,
    ))

    fig.update_layout(
        title=f"Reported vs Actual ROAS Trend ({window}-Day Rolling)",
        yaxis_title="ROAS",
        template="plotly_white",
        height=350,
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
    )
    return fig


def cannibalization_trend_chart(result: AuditResult, window: int = 14) -> go.Figure:
    """Rolling cannibalization indicator over time (requires brand_clicks)."""
    df = result.daily_df
    if df is None or df.empty or "brand_clicks" not in df.columns:
        return go.Figure()

    conv_avg = df["reported_conversions"].rolling(window, min_periods=1).mean()
    brand_avg = df["brand_clicks"].rolling(window, min_periods=1).mean()

    # Cannibalized = both above their averages on spend-on days
    is_cannibalized = (
        (df["reported_conversions"] > conv_avg)
        & (df["brand_clicks"] > brand_avg)
        & (df["spend"] > 0)
    ).astype(float)

    rolling_score = is_cannibalized.rolling(window, min_periods=1).mean()

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df["date"], y=rolling_score,
        mode="lines",
        name=f"Cannibalization Score ({window}-day rolling)",
        line=dict(color="#FFA15A", width=2),
        fill="tozeroy",
        fillcolor="rgba(255, 161, 90, 0.15)",
    ))

    fig.update_layout(
        title=f"Cannibalization Score Trend ({window}-Day Rolling)",
        yaxis_title="Cannibalization Score",
        yaxis_tickformat=".0%",
        template="plotly_white",
        height=350,
    )
    return fig


def organic_vs_incremental_trend(result: AuditResult, window: int = 7) -> go.Figure:
    """Stacked area: organic baseline vs incremental conversions over time."""
    df = result.daily_df
    if df is None or df.empty:
        return go.Figure()

    rolling_actual = df["actual_conversions"].rolling(window, min_periods=1).mean()
    organic = result.organic_baseline_conversions

    incremental = np.maximum(0, rolling_actual - organic)

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df["date"],
        y=[organic] * len(df),
        mode="lines",
        name="Organic Baseline",
        line=dict(color="#636EFA", width=1, dash="dash"),
        fill="tozeroy",
        fillcolor="rgba(99, 110, 250, 0.1)",
    ))
    fig.add_trace(go.Scatter(
        x=df["date"],
        y=rolling_actual,
        mode="lines",
        name=f"Actual Conversions ({window}-day avg)",
        line=dict(color="#00CC96", width=2),
        fill="tonexty",
        fillcolor="rgba(0, 204, 150, 0.15)",
    ))

    fig.update_layout(
        title=f"Organic Baseline vs Actual Conversions ({window}-Day Rolling Avg)",
        yaxis_title="Conversions / Day",
        template="plotly_white",
        height=350,
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
    )
    return fig
