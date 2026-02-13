"""Google Ads API connector.

Fetches campaign-level daily metrics and optional search term reports via
the Google Ads API (REST interface) and returns normalized DataFrames.

Requires:
    - Customer ID (e.g. "1234567890")
    - Developer Token
    - OAuth2 credentials (client_id, client_secret, refresh_token)

See: https://developers.google.com/google-ads/api/docs/start
"""

from __future__ import annotations

from datetime import date, timedelta

import pandas as pd

from ad_audit.connectors.base import BaseConnector, ConnectorConfig
from ad_audit.ingestion.normalizer import normalize_google_ads, normalize_search_terms


class GoogleAdsConnector(BaseConnector):
    """Pull Google Ads data via the REST API (using GAQL queries)."""

    API_VERSION = "v16"

    def __init__(
        self,
        customer_id: str,
        developer_token: str,
        client_id: str,
        client_secret: str,
        refresh_token: str,
    ):
        self.customer_id = customer_id.replace("-", "")
        self.developer_token = developer_token
        self.client_id = client_id
        self.client_secret = client_secret
        self.refresh_token = refresh_token
        self._base_url = (
            f"https://googleads.googleapis.com/{self.API_VERSION}"
            f"/customers/{self.customer_id}/googleAds:searchStream"
        )

    @property
    def source_name(self) -> str:
        return "Google Ads"

    def test_connection(self) -> bool:
        """Verify credentials with a simple account query."""
        try:
            token = self._get_access_token()
            import requests

            resp = requests.post(
                self._base_url,
                headers=self._headers(token),
                json={"query": "SELECT customer.id FROM customer LIMIT 1"},
                timeout=10,
            )
            return resp.status_code == 200
        except Exception:
            return False

    def fetch_data(self, config: ConnectorConfig | None = None) -> pd.DataFrame:
        """Fetch daily campaign metrics and return a normalized DataFrame."""
        if config is None:
            config = ConnectorConfig()

        start = config.start_date or (date.today() - timedelta(days=60))
        end = config.end_date or date.today()

        query = f"""
            SELECT
                segments.date,
                campaign.name,
                metrics.cost_micros,
                metrics.conversions,
                metrics.conversions_value,
                metrics.cost_per_conversion
            FROM campaign
            WHERE segments.date BETWEEN '{start}' AND '{end}'
            ORDER BY segments.date
        """

        rows = self._run_query(query)
        if not rows:
            return pd.DataFrame()

        records = []
        for row in rows:
            segments = row.get("segments", {})
            campaign = row.get("campaign", {})
            metrics = row.get("metrics", {})
            cost = float(metrics.get("costMicros", 0)) / 1_000_000
            records.append({
                "Day": segments.get("date", ""),
                "Campaign": campaign.get("name", ""),
                "Cost": round(cost, 2),
                "Conversions": float(metrics.get("conversions", 0)),
                "Conv. value": float(metrics.get("conversionsValue", 0)),
                "Cost / conv.": float(metrics.get("costPerConversion", 0)) / 1_000_000,
            })

        raw_df = pd.DataFrame(records)
        return normalize_google_ads(raw_df)

    def fetch_search_terms(self, config: ConnectorConfig | None = None) -> pd.DataFrame:
        """Fetch search term report and return a normalized DataFrame."""
        if config is None:
            config = ConnectorConfig()

        start = config.start_date or (date.today() - timedelta(days=60))
        end = config.end_date or date.today()

        query = f"""
            SELECT
                search_term_view.search_term,
                campaign.name,
                ad_group.name,
                metrics.cost_micros,
                metrics.conversions,
                metrics.impressions,
                metrics.clicks,
                metrics.conversions_value
            FROM search_term_view
            WHERE segments.date BETWEEN '{start}' AND '{end}'
            ORDER BY metrics.cost_micros DESC
        """

        rows = self._run_query(query)
        if not rows:
            return pd.DataFrame()

        records = []
        for row in rows:
            stv = row.get("searchTermView", {})
            campaign = row.get("campaign", {})
            ad_group = row.get("adGroup", {})
            metrics = row.get("metrics", {})
            cost = float(metrics.get("costMicros", 0)) / 1_000_000
            records.append({
                "Search term": stv.get("searchTerm", ""),
                "Campaign": campaign.get("name", ""),
                "Ad group": ad_group.get("name", ""),
                "Cost": round(cost, 2),
                "Conversions": float(metrics.get("conversions", 0)),
                "Impressions": int(metrics.get("impressions", 0)),
                "Clicks": int(metrics.get("clicks", 0)),
                "Conv. value": float(metrics.get("conversionsValue", 0)),
            })

        raw_df = pd.DataFrame(records)
        return normalize_search_terms(raw_df)

    def _run_query(self, query: str) -> list[dict]:
        """Execute a GAQL query and return result rows."""
        import requests

        token = self._get_access_token()
        resp = requests.post(
            self._base_url,
            headers=self._headers(token),
            json={"query": query},
            timeout=60,
        )
        resp.raise_for_status()

        rows: list[dict] = []
        for batch in resp.json():
            rows.extend(batch.get("results", []))
        return rows

    def _get_access_token(self) -> str:
        """Exchange refresh token for an access token."""
        import requests

        resp = requests.post(
            "https://oauth2.googleapis.com/token",
            data={
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "refresh_token": self.refresh_token,
                "grant_type": "refresh_token",
            },
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json()["access_token"]

    def _headers(self, access_token: str) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {access_token}",
            "developer-token": self.developer_token,
            "Content-Type": "application/json",
        }
