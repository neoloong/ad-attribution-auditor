"""Page 2: Configure and run the audit."""

import streamlit as st
import pandas as pd

from ad_audit.engine.models import AuditConfig, AuditMode
from ad_audit.engine.aggregate_audit import run_aggregate_audit
from ad_audit.engine.user_level_audit import run_user_level_audit


st.set_page_config(page_title="Run Audit", page_icon="🔬", layout="wide")
st.title("🔬 Run Audit")

if "audit_result" not in st.session_state:
    st.session_state["audit_result"] = None

# Check data availability
meta_df = st.session_state.get("meta_df")
google_ads_df = st.session_state.get("google_ads_df")
shopify_df = st.session_state.get("shopify_df")
gsc_df = st.session_state.get("gsc_df")
user_df = st.session_state.get("user_df")

has_ad_platform = meta_df is not None or google_ads_df is not None
has_aggregate_data = has_ad_platform and shopify_df is not None
has_user_data = user_df is not None

if not has_aggregate_data and not has_user_data:
    st.warning("Please upload data on the **Upload Data** page first.  \n"
               "Aggregate mode needs at least **one ad platform** (Meta or Google Ads) + **Shopify Orders**.  \n"
               "User-Level mode needs **User-Matched Events**.")
    st.stop()

# Mode selection
st.markdown("### Audit Mode")

available_modes = []
if has_aggregate_data:
    # Build descriptive label
    platforms = []
    if meta_df is not None:
        platforms.append("Meta")
    if google_ads_df is not None:
        platforms.append("Google Ads")
    label = f"Aggregate (time-series) — {' + '.join(platforms)}"
    if gsc_df is None:
        label += " — GSC not loaded, cannibalization will be skipped"
    available_modes.append(label)
if has_user_data:
    available_modes.append("User-Level (email/click-ID matching)")

mode_label = st.radio("Select audit approach:", available_modes)

is_aggregate = "Aggregate" in mode_label

# Configuration
st.markdown("### Configuration")
col1, col2 = st.columns(2)

with col1:
    attribution_window = st.slider(
        "Attribution window (days)", 1, 30, 7, help="Click-to-purchase window for ad attribution"
    )
    spend_threshold = st.number_input(
        "Spend-on threshold ($)", 0.0, 1000.0, 5.0, help="Min daily spend to count as 'spend on'"
    )

with col2:
    cannibalization_lookback = st.slider(
        "Cannibalization lookback (hours)", 1, 72, 24,
        help="How far back to check for brand searches before a click",
    )
    correlation_window = st.slider(
        "Correlation window (days)", 3, 30, 7, help="Rolling window for Pearson correlation"
    )

config = AuditConfig(
    mode=AuditMode.AGGREGATE if is_aggregate else AuditMode.USER_LEVEL,
    attribution_window_days=attribution_window,
    cannibalization_lookback_hours=cannibalization_lookback,
    spend_on_threshold=spend_threshold,
    correlation_window_days=correlation_window,
)

# Run
st.markdown("---")
if st.button("Run Audit", type="primary"):
    with st.spinner("Running audit..."):
        try:
            if is_aggregate:
                # Concatenate whichever ad platform DataFrames are available
                ad_dfs = [df for df in (meta_df, google_ads_df) if df is not None]
                ad_df = pd.concat(ad_dfs, ignore_index=True)
                result = run_aggregate_audit(ad_df, shopify_df, gsc_df, config)
                # Store ad_df for period comparison
                st.session_state["_last_ad_df"] = ad_df
            else:
                result = run_user_level_audit(user_df, config)

            st.session_state["audit_result"] = result

            # Run search term analysis if data is available
            search_terms_df = st.session_state.get("search_terms_df")
            if search_terms_df is not None and shopify_df is not None:
                from ad_audit.engine.search_term_analysis import analyze_search_terms
                st_result = analyze_search_terms(search_terms_df, shopify_df)
                st.session_state["search_terms_result"] = st_result

            st.success("Audit complete! Navigate to the **Dashboard** to see results.")

            # Quick summary
            summary = result.summary_dict
            st.json(summary)

        except Exception as e:
            st.error(f"Audit failed: {e}")
            raise
