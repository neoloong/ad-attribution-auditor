"""Meta Marketing API connector.

Fetches campaign-level daily insights via the Meta Marketing API and returns
a normalized DataFrame compatible with the ingestion pipeline.

Requires:
    - Ad Account ID (e.g. "act_123456789")
    - Access Token (long-lived user or system user token)

See: https://developers.facebook.com/docs/marketing-api/insights
"""

from __future__ import annotations

from datetime import date, timedelta

import pandas as pd

from ad_audit.connectors.base import BaseConnector, ConnectorConfig
from ad_audit.ingestion.normalizer import normalize_meta_ads


class MetaAdsConnector(BaseConnector):
    """Pull Meta Ads insights via the Marketing API."""

    API_VERSION = "v19.0"

    def __init__(self, ad_account_id: str, access_token: str):
        self.ad_account_id = ad_account_id
        self.access_token = access_token
        self._base_url = f"https://graph.facebook.com/{self.API_VERSION}"

    @property
    def source_name(self) -> str:
        return "Meta Ads"

    def test_connection(self) -> bool:
        """Verify credentials by fetching account info."""
        import requests

        resp = requests.get(
            f"{self._base_url}/{self.ad_account_id}",
            params={"access_token": self.access_token, "fields": "name,account_status"},
            timeout=10,
        )
        return resp.status_code == 200

    def fetch_data(self, config: ConnectorConfig | None = None) -> pd.DataFrame:
        """Fetch daily campaign insights and return a normalized DataFrame."""
        import requests

        if config is None:
            config = ConnectorConfig()

        start = config.start_date or (date.today() - timedelta(days=60))
        end = config.end_date or date.today()

        rows: list[dict] = []
        url = f"{self._base_url}/{self.ad_account_id}/insights"
        params = {
            "access_token": self.access_token,
            "fields": "campaign_name,spend,actions,action_values",
            "level": "campaign",
            "time_increment": 1,
            "time_range": f'{{"since":"{start}","until":"{end}"}}',
            "limit": 500,
        }

        while url:
            resp = requests.get(url, params=params, timeout=30)
            resp.raise_for_status()
            data = resp.json()

            for row in data.get("data", []):
                purchases = 0
                purchase_value = 0
                for action in row.get("actions", []):
                    if action.get("action_type") == "purchase":
                        purchases = int(action.get("value", 0))
                for av in row.get("action_values", []):
                    if av.get("action_type") == "purchase":
                        purchase_value = float(av.get("value", 0))

                spend = float(row.get("spend", 0))
                roas = purchase_value / spend if spend > 0 else 0

                rows.append({
                    "Day": row.get("date_start", ""),
                    "Campaign name": row.get("campaign_name", ""),
                    "Amount spent (USD)": spend,
                    "Purchases": purchases,
                    "Purchase conversion value": purchase_value,
                    "Purchase ROAS": round(roas, 2),
                })

            # Pagination
            url = data.get("paging", {}).get("next")
            params = None  # next URL has params baked in

        if not rows:
            return pd.DataFrame()

        raw_df = pd.DataFrame(rows)
        return normalize_meta_ads(raw_df)
