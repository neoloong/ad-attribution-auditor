"""Page 5: API connector configuration for automatic data pulls."""

import streamlit as st

st.set_page_config(page_title="API Connections", page_icon="🔌", layout="wide")
st.title("🔌 API Connections")

st.markdown(
    """
Connect directly to your ad platforms and e-commerce store for automatic data
pulls — no CSV uploads needed.

> **Note**: API connections require credentials from each platform.
> Your credentials are only stored in your browser session and are never saved
> to disk.
"""
)

# Initialize session state for connectors
for key in ("shopify_connector", "meta_connector", "google_ads_connector"):
    if key not in st.session_state:
        st.session_state[key] = None

# --- Shopify ---
st.markdown("---")
st.markdown("### Shopify Admin API")
with st.expander("Configure Shopify connection"):
    shop_domain = st.text_input(
        "Shop domain", placeholder="mystore.myshopify.com", key="shopify_domain"
    )
    shop_token = st.text_input(
        "Admin API access token", type="password", key="shopify_token"
    )

    if st.button("Test Shopify Connection"):
        if shop_domain and shop_token:
            try:
                from ad_audit.connectors.shopify_api import ShopifyConnector

                connector = ShopifyConnector(shop_domain, shop_token)
                if connector.test_connection():
                    st.session_state["shopify_connector"] = connector
                    st.success("Connected to Shopify!")
                else:
                    st.error("Connection failed. Check your domain and token.")
            except Exception as e:
                st.error(f"Connection error: {e}")
        else:
            st.warning("Please enter both shop domain and access token.")

# --- Meta Ads ---
st.markdown("---")
st.markdown("### Meta Marketing API")
with st.expander("Configure Meta Ads connection"):
    meta_account = st.text_input(
        "Ad Account ID", placeholder="act_123456789", key="meta_account"
    )
    meta_token = st.text_input(
        "Access token", type="password", key="meta_token"
    )

    if st.button("Test Meta Ads Connection"):
        if meta_account and meta_token:
            try:
                from ad_audit.connectors.meta_api import MetaAdsConnector

                connector = MetaAdsConnector(meta_account, meta_token)
                if connector.test_connection():
                    st.session_state["meta_connector"] = connector
                    st.success("Connected to Meta Ads!")
                else:
                    st.error("Connection failed. Check your account ID and token.")
            except Exception as e:
                st.error(f"Connection error: {e}")
        else:
            st.warning("Please enter both account ID and access token.")

# --- Google Ads ---
st.markdown("---")
st.markdown("### Google Ads API")
with st.expander("Configure Google Ads connection"):
    gads_customer = st.text_input(
        "Customer ID", placeholder="123-456-7890", key="gads_customer"
    )
    gads_dev_token = st.text_input(
        "Developer token", type="password", key="gads_dev_token"
    )
    gads_client_id = st.text_input("OAuth Client ID", key="gads_client_id")
    gads_client_secret = st.text_input(
        "OAuth Client Secret", type="password", key="gads_client_secret"
    )
    gads_refresh = st.text_input(
        "OAuth Refresh Token", type="password", key="gads_refresh"
    )

    if st.button("Test Google Ads Connection"):
        if all([gads_customer, gads_dev_token, gads_client_id, gads_client_secret, gads_refresh]):
            try:
                from ad_audit.connectors.google_ads_api import GoogleAdsConnector

                connector = GoogleAdsConnector(
                    gads_customer, gads_dev_token,
                    gads_client_id, gads_client_secret, gads_refresh,
                )
                if connector.test_connection():
                    st.session_state["google_ads_connector"] = connector
                    st.success("Connected to Google Ads!")
                else:
                    st.error("Connection failed. Check your credentials.")
            except Exception as e:
                st.error(f"Connection error: {e}")
        else:
            st.warning("Please fill in all Google Ads fields.")

# --- Fetch Data ---
st.markdown("---")
st.markdown("### Pull Data from APIs")

col1, col2 = st.columns(2)
with col1:
    start_date = st.date_input("Start date", value=None, key="api_start")
with col2:
    end_date = st.date_input("End date", value=None, key="api_end")

if st.button("Fetch All Connected Data", type="primary"):
    from ad_audit.connectors.base import ConnectorConfig

    api_config = ConnectorConfig(start_date=start_date, end_date=end_date)

    # Shopify
    if st.session_state.get("shopify_connector"):
        with st.spinner("Fetching Shopify orders..."):
            try:
                df = st.session_state["shopify_connector"].fetch_data(api_config)
                st.session_state["shopify_df"] = df
                st.success(f"Shopify: {len(df)} orders fetched.")
            except Exception as e:
                st.error(f"Shopify fetch failed: {e}")

    # Meta Ads
    if st.session_state.get("meta_connector"):
        with st.spinner("Fetching Meta Ads data..."):
            try:
                df = st.session_state["meta_connector"].fetch_data(api_config)
                st.session_state["meta_df"] = df
                st.success(f"Meta Ads: {len(df)} rows fetched.")
            except Exception as e:
                st.error(f"Meta Ads fetch failed: {e}")

    # Google Ads
    if st.session_state.get("google_ads_connector"):
        with st.spinner("Fetching Google Ads data..."):
            try:
                connector = st.session_state["google_ads_connector"]
                df = connector.fetch_data(api_config)
                st.session_state["google_ads_df"] = df
                st.success(f"Google Ads: {len(df)} rows fetched.")

                # Also fetch search terms
                st_df = connector.fetch_search_terms(api_config)
                if not st_df.empty:
                    st.session_state["search_terms_df"] = st_df
                    st.success(f"Search terms: {len(st_df)} terms fetched.")
            except Exception as e:
                st.error(f"Google Ads fetch failed: {e}")

    if not any(st.session_state.get(k) for k in ("shopify_connector", "meta_connector", "google_ads_connector")):
        st.warning("No API connections configured. Set up at least one above.")

# Connection status
st.markdown("---")
st.markdown("### Connection Status")
for key, label in [
    ("shopify_connector", "Shopify"),
    ("meta_connector", "Meta Ads"),
    ("google_ads_connector", "Google Ads"),
]:
    connected = st.session_state.get(key) is not None
    status = "Connected" if connected else "Not configured"
    icon = "🟢" if connected else "⚪"
    st.markdown(f"- {icon} **{label}**: {status}")
