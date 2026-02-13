"""Ad Attribution Auditor — Streamlit entry point."""

import streamlit as st

st.set_page_config(
    page_title="Ad Attribution Auditor",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.sidebar.title("🔍 Ad Attribution Auditor")
st.sidebar.markdown(
    """
*Don't let Big Tech grade their own homework.*

---
**How to use:**
1. **Upload Data** — CSV files or connect via API
2. **Run Audit** — Choose aggregate or user-level mode
3. **Dashboard** — Health checks, trends, charts, and KPIs
4. **Report** — Generate an AI-powered summary and download
5. **API Connections** — Connect directly to Shopify, Meta, and Google Ads
"""
)

st.title("Ad Attribution Auditor")
st.markdown(
    """
Welcome to the **Ad Attribution Auditor** — an independent tool that audits
ad platform attribution claims by cross-referencing your actual e-commerce sales
data with Meta Ads and/or Google Ads reports, plus optional Google Search Console
brand-search metrics.

### What this tool does

- **De-duplication**: Identifies conversions that ad platforms over-count
- **Cannibalization Detection**: Finds users who would have purchased anyway
  (they were already searching for your brand)
- **True Incremental ROAS**: Calculates your real return on ad spend after
  removing inflated claims
- **Health Check Alerts**: Automated warnings when metrics cross thresholds
- **Trend Analysis**: Rolling metrics over time — see if things are getting better or worse
- **Period Comparison**: Split by date to see what changed and why
- **Search Term Analysis**: Find wasted spend on terms with no verified purchases
- **API Connections**: Connect directly to Shopify, Meta Ads, and Google Ads

👈 **Get started by navigating to the Upload Data page in the sidebar.**
"""
)
