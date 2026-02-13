"""Streamlit layout components for the dashboard."""

from __future__ import annotations

from typing import Any

import streamlit as st

from ad_audit.engine.models import AuditResult


def render_kpi_cards(result: AuditResult) -> None:
    """Display top-level KPI cards in a Streamlit row."""
    ir = result.incremental_roas

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            label="Reported ROAS",
            value=f"{ir.reported_roas:.2f}x",
        )

    with col2:
        st.metric(
            label="True Incremental ROAS",
            value=f"{ir.true_incremental_roas:.2f}x",
            delta=f"-{ir.inflation_rate:.0%}" if ir.inflation_rate > 0 else None,
            delta_color="inverse",
        )

    with col3:
        st.metric(
            label="Duplication Rate",
            value=f"{result.deduplication.duplication_rate:.1%}",
        )

    with col4:
        st.metric(
            label="Cannibalization Score",
            value=f"{result.cannibalization.cannibalization_score:.1%}",
        )


def render_secondary_kpis(result: AuditResult) -> None:
    """Second row of KPI cards."""
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            label="Organic Baseline (conv/day)",
            value=f"{result.organic_baseline_conversions:.1f}",
        )

    with col2:
        st.metric(
            label="Incremental Conv/Day",
            value=f"{result.incremental_conversions_per_day:.1f}",
        )

    with col3:
        st.metric(
            label="Spend-Conversion Correlation",
            value=f"{result.correlation_mean:.2f}",
        )


def render_user_level_kpis(result: AuditResult) -> None:
    """KPI cards specific to user-level audit."""
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            label="Matched Orders",
            value=f"{result.total_matched_orders:,}",
        )

    with col2:
        st.metric(
            label="Truly Incremental",
            value=f"{result.truly_incremental_orders:,}",
        )

    with col3:
        st.metric(
            label="Cannibalized Orders",
            value=f"{result.cannibalized_orders:,}",
        )


def data_preview(label: str, df: Any, max_rows: int = 10) -> None:
    """Show a collapsible data preview."""
    if df is not None and len(df) > 0:
        with st.expander(f"{label} ({len(df)} rows)"):
            st.dataframe(df.head(max_rows), use_container_width=True)
