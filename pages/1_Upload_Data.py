"""Page 1: Upload & validate CSV data."""

from pathlib import Path

import streamlit as st
import pandas as pd

from ad_audit.ingestion.loader import load_csv
from ad_audit.ingestion.validators import validate_schema
from ad_audit.ingestion.normalizer import (
    normalize_meta_ads,
    normalize_google_ads,
    normalize_shopify_orders,
    normalize_gsc,
    normalize_search_terms,
    normalize_user_matched,
)

st.set_page_config(page_title="Upload Data", page_icon="📁", layout="wide")
st.title("📁 Upload Data")

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

# Initialize session state
for key in ("meta_df", "google_ads_df", "shopify_df", "gsc_df", "search_terms_df", "user_df"):
    if key not in st.session_state:
        st.session_state[key] = None


def _upload_and_validate(label: str, schema_name: str, normalize_fn, state_key: str):
    """Upload widget + validation for a single CSV type."""
    uploaded = st.file_uploader(f"Upload {label} CSV", type=["csv"], key=f"upload_{state_key}")
    if uploaded is not None:
        df = load_csv(uploaded)
        result = validate_schema(df, schema_name)
        if result.valid:
            normalized = normalize_fn(df)
            st.session_state[state_key] = normalized
            st.success(f"{label}: {len(normalized)} rows loaded successfully.")
            with st.expander("Preview"):
                st.dataframe(normalized.head(10), use_container_width=True)
        else:
            st.error(f"Missing required columns: {result.missing_required}")
            if result.missing_optional:
                st.warning(f"Missing optional columns: {result.missing_optional}")


# Load Sample Data button
st.markdown("### Quick Start")
if st.button("Load Sample Data", type="primary"):
    try:
        meta = load_csv(DATA_DIR / "sample_meta_ads.csv")
        st.session_state["meta_df"] = normalize_meta_ads(meta)

        google_ads = load_csv(DATA_DIR / "sample_google_ads.csv")
        st.session_state["google_ads_df"] = normalize_google_ads(google_ads)

        shopify = load_csv(DATA_DIR / "sample_shopify_orders.csv")
        st.session_state["shopify_df"] = normalize_shopify_orders(shopify)

        gsc = load_csv(DATA_DIR / "sample_gsc_brand_search.csv")
        st.session_state["gsc_df"] = normalize_gsc(gsc)

        search_terms = load_csv(DATA_DIR / "sample_search_terms.csv")
        st.session_state["search_terms_df"] = normalize_search_terms(search_terms)

        user = load_csv(DATA_DIR / "sample_user_matched.csv")
        st.session_state["user_df"] = normalize_user_matched(user)

        st.success("Sample data loaded! Navigate to **Run Audit** to continue.")
    except Exception as e:
        st.error(f"Could not load sample data: {e}")

st.markdown("---")
st.markdown("### Upload Your Own Data")

st.markdown("**Required: at least one ad platform**")
col1, col2 = st.columns(2)
with col1:
    _upload_and_validate("Meta Ads", "meta_ads", normalize_meta_ads, "meta_df")
with col2:
    _upload_and_validate("Google Ads", "google_ads", normalize_google_ads, "google_ads_df")

st.markdown("**Required: Shopify Orders**")
_upload_and_validate("Shopify Orders", "shopify_orders", normalize_shopify_orders, "shopify_df")

st.markdown("**Optional (enhances analysis):**")
col3, col4 = st.columns(2)
with col3:
    _upload_and_validate(
        "Google Search Console — Brand Search (adds cannibalization scoring)",
        "gsc_brand_search",
        normalize_gsc,
        "gsc_df",
    )
with col4:
    _upload_and_validate(
        "Google Ads Search Terms (adds wasted spend analysis)",
        "search_terms",
        normalize_search_terms,
        "search_terms_df",
    )

col5, col6 = st.columns(2)
with col5:
    _upload_and_validate(
        "User-Matched Events (enables User-Level audit mode)",
        "user_matched",
        normalize_user_matched,
        "user_df",
    )

# Status summary
st.markdown("---")
st.markdown("### Data Status")
for key, label in [
    ("meta_df", "Meta Ads"),
    ("google_ads_df", "Google Ads"),
    ("shopify_df", "Shopify Orders"),
    ("gsc_df", "GSC Brand Search"),
    ("search_terms_df", "Search Terms"),
    ("user_df", "User-Matched Events"),
]:
    df = st.session_state.get(key)
    if df is not None:
        st.markdown(f"- **{label}**: {len(df)} rows ✅")
    else:
        st.markdown(f"- **{label}**: Not loaded")
