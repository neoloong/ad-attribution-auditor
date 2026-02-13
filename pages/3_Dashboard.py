"""Page 3: Interactive dashboard with charts, KPIs, health checks, and trends."""

import streamlit as st
import pandas as pd

from ad_audit.engine.models import AuditMode
from ad_audit.engine.health_checks import run_health_checks, Severity
from ad_audit.visualization.charts import (
    reported_vs_true_roas_bar,
    spend_vs_conversions_dual_axis,
    revenue_waterfall,
    attribution_breakdown_pie,
    brand_search_overlap_chart,
)
from ad_audit.visualization.trend_charts import (
    rolling_duplication_rate_chart,
    rolling_roas_comparison_chart,
    cannibalization_trend_chart,
    organic_vs_incremental_trend,
)
from ad_audit.visualization.dashboard import (
    render_kpi_cards,
    render_secondary_kpis,
    render_user_level_kpis,
    data_preview,
)

st.set_page_config(page_title="Dashboard", page_icon="📊", layout="wide")
st.title("📊 Audit Dashboard")

result = st.session_state.get("audit_result")

if result is None:
    st.warning("No audit results yet. Please run an audit first.")
    st.stop()

# --- Health Check Alerts ---
st.markdown("### Health Check Alerts")

alerts = run_health_checks(result)

if not alerts:
    st.success("All health checks passed — no issues detected.")
else:
    for alert in alerts:
        if alert.severity == Severity.CRITICAL:
            st.error(f"**{alert.title}**: {alert.message}")
        elif alert.severity == Severity.WARNING:
            st.warning(f"**{alert.title}**: {alert.message}")
        else:
            st.info(f"**{alert.title}**: {alert.message}")

st.markdown("---")

# --- KPI Cards ---
st.markdown("### Key Metrics")
render_kpi_cards(result)

if result.mode == AuditMode.AGGREGATE:
    render_secondary_kpis(result)
else:
    render_user_level_kpis(result)

st.markdown("---")

# --- Core Charts ---
st.markdown("### Charts")

col1, col2 = st.columns(2)

with col1:
    st.plotly_chart(reported_vs_true_roas_bar(result), use_container_width=True)

with col2:
    st.plotly_chart(attribution_breakdown_pie(result), use_container_width=True)

if result.mode == AuditMode.AGGREGATE and result.daily_df is not None:
    st.plotly_chart(spend_vs_conversions_dual_axis(result), use_container_width=True)

    col3, col4 = st.columns(2)
    with col3:
        st.plotly_chart(revenue_waterfall(result), use_container_width=True)
    with col4:
        st.plotly_chart(brand_search_overlap_chart(result), use_container_width=True)

    # --- Trend Charts ---
    st.markdown("---")
    st.markdown("### Trends Over Time")

    trend_window = st.slider(
        "Rolling window (days)", 3, 30, 7, key="trend_window",
        help="Window size for rolling metric calculations",
    )

    col5, col6 = st.columns(2)
    with col5:
        fig = rolling_duplication_rate_chart(result, window=trend_window)
        if fig.data:
            st.plotly_chart(fig, use_container_width=True)

    with col6:
        fig = rolling_roas_comparison_chart(result, window=trend_window)
        if fig.data:
            st.plotly_chart(fig, use_container_width=True)

    col7, col8 = st.columns(2)
    with col7:
        fig = cannibalization_trend_chart(result, window=trend_window)
        if fig.data:
            st.plotly_chart(fig, use_container_width=True)

    with col8:
        fig = organic_vs_incremental_trend(result, window=trend_window)
        if fig.data:
            st.plotly_chart(fig, use_container_width=True)

    # --- Period-over-Period Comparison ---
    st.markdown("---")
    st.markdown("### Period-over-Period Comparison")
    st.markdown("Split your data at a date to compare two periods and see what changed.")

    daily = result.daily_df
    if daily is not None and len(daily) > 1:
        min_date = daily["date"].min()
        max_date = daily["date"].max()
        midpoint = min_date + (max_date - min_date) / 2

        split_date = st.date_input(
            "Split date (Period 1: before, Period 2: on or after)",
            value=midpoint.date() if hasattr(midpoint, "date") else midpoint,
            min_value=min_date.date() if hasattr(min_date, "date") else min_date,
            max_value=max_date.date() if hasattr(max_date, "date") else max_date,
            key="split_date",
        )

        if st.button("Compare Periods"):
            from ad_audit.engine.period_comparison import compare_periods

            ad_df = st.session_state.get("_last_ad_df")
            shopify_df = st.session_state.get("shopify_df")
            gsc_df = st.session_state.get("gsc_df")

            if ad_df is not None and shopify_df is not None:
                with st.spinner("Comparing periods..."):
                    comparison = compare_periods(
                        ad_df, shopify_df, split_date, gsc_df, result.config
                    )

                st.markdown(f"**{comparison.period_1_label}** vs **{comparison.period_2_label}**")

                # Deltas table
                delta_rows = []
                for d in comparison.deltas:
                    pct_str = f"{d.percent_change:+.1%}" if d.percent_change is not None else "N/A"
                    delta_rows.append({
                        "Metric": d.label,
                        "Period 1": f"{d.period_1_value:.4f}",
                        "Period 2": f"{d.period_2_value:.4f}",
                        "Change": f"{d.absolute_change:+.4f}",
                        "% Change": pct_str,
                    })
                st.dataframe(pd.DataFrame(delta_rows), use_container_width=True)

                # Root causes
                st.markdown("#### Root Cause Analysis")
                for cause in comparison.root_causes:
                    st.markdown(f"- {cause}")
            else:
                st.warning(
                    "Period comparison requires the original ad and Shopify DataFrames. "
                    "Please re-run the audit from the Run Audit page."
                )

# --- Search Term Analysis ---
search_terms_result = st.session_state.get("search_terms_result")
if search_terms_result is not None and search_terms_result.total_terms > 0:
    st.markdown("---")
    st.markdown("### Search Term Wasted Spend Analysis")

    col_st1, col_st2, col_st3 = st.columns(3)
    with col_st1:
        st.metric("Total Search Term Spend", f"${search_terms_result.total_spend:,.0f}")
    with col_st2:
        st.metric("Wasted Spend", f"${search_terms_result.wasted_spend:,.0f}")
    with col_st3:
        st.metric("Wasted %", f"{search_terms_result.wasted_spend_pct:.1%}")

    if search_terms_result.summary_df is not None:
        st.markdown("#### Top Wasted Spend Terms")
        wasted_df = search_terms_result.summary_df[
            search_terms_result.summary_df["wasted_spend"] > 0
        ].head(20)
        if not wasted_df.empty:
            st.dataframe(wasted_df, use_container_width=True)
        else:
            st.info("No terms with zero verified orders found.")

        if search_terms_result.brand_term_spend > 0:
            st.markdown("#### Brand Term Insight")
            st.markdown(
                f"Brand terms accounted for **${search_terms_result.brand_term_spend:,.0f}** "
                f"in spend with **{search_terms_result.brand_term_verified_orders}** verified orders. "
                f"These users may have purchased organically."
            )

# --- Data Previews ---
st.markdown("---")
st.markdown("### Data Preview")

if result.daily_df is not None:
    data_preview("Daily Merged Data", result.daily_df, max_rows=15)

if result.user_match_df is not None:
    data_preview("User Match Data", result.user_match_df, max_rows=15)
