"""Shopify Admin API connector.

Fetches orders via Shopify's REST Admin API and returns a normalized
DataFrame compatible with the ingestion pipeline.

Requires:
    - Shop domain (e.g. "mystore.myshopify.com")
    - Admin API access token

See: https://shopify.dev/docs/api/admin-rest/2024-01/resources/order
"""

from __future__ import annotations

from datetime import date, timedelta

import pandas as pd

from ad_audit.connectors.base import BaseConnector, ConnectorConfig
from ad_audit.ingestion.normalizer import normalize_shopify_orders


class ShopifyConnector(BaseConnector):
    """Pull Shopify orders via REST Admin API."""

    def __init__(self, shop_domain: str, access_token: str):
        self.shop_domain = shop_domain.rstrip("/")
        self.access_token = access_token
        self._base_url = f"https://{self.shop_domain}/admin/api/2024-01"

    @property
    def source_name(self) -> str:
        return "Shopify"

    def test_connection(self) -> bool:
        """Verify credentials by fetching shop info."""
        import requests

        resp = requests.get(
            f"{self._base_url}/shop.json",
            headers=self._headers(),
            timeout=10,
        )
        return resp.status_code == 200

    def fetch_data(self, config: ConnectorConfig | None = None) -> pd.DataFrame:
        """Fetch orders and return a normalized DataFrame."""
        import requests

        if config is None:
            config = ConnectorConfig()

        start = config.start_date or (date.today() - timedelta(days=60))
        end = config.end_date or date.today()

        orders: list[dict] = []
        url = f"{self._base_url}/orders.json"
        params = {
            "status": "any",
            "created_at_min": f"{start}T00:00:00Z",
            "created_at_max": f"{end}T23:59:59Z",
            "limit": 250,
            "fields": "name,email,created_at,total_price,referring_site,landing_site",
        }

        while url:
            resp = requests.get(url, headers=self._headers(), params=params, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            orders.extend(data.get("orders", []))

            # Pagination via Link header
            url = None
            params = None
            link = resp.headers.get("Link", "")
            if 'rel="next"' in link:
                for part in link.split(","):
                    if 'rel="next"' in part:
                        url = part.split(";")[0].strip(" <>")
                        break

        if not orders:
            return pd.DataFrame()

        # Map to expected CSV column names
        rows = []
        for o in orders:
            rows.append({
                "Name": o.get("name", ""),
                "Email": o.get("email", ""),
                "Created at": o.get("created_at", ""),
                "Total": o.get("total_price", 0),
                "Referring Site": o.get("referring_site", ""),
                "Landing Site": o.get("landing_site", ""),
            })

        raw_df = pd.DataFrame(rows)
        return normalize_shopify_orders(raw_df)

    def _headers(self) -> dict[str, str]:
        return {
            "X-Shopify-Access-Token": self.access_token,
            "Content-Type": "application/json",
        }
