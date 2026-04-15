"""Tests for ShopifyConnector using mocked HTTP responses."""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch


class TestShopifyConnector:
    """Unit tests for ShopifyConnector with mocked HTTP responses."""

    @pytest.fixture
    def connector(self):
        from ad_audit.connectors.shopify_api import ShopifyConnector

        conn = ShopifyConnector("test-shop.myshopify.com", "fake_token")
        return conn

    # ---- test_connection ----

    def test_test_connection_success(self, connector):
        """test_connection returns True when shop.json returns 200."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200

        with patch("requests.get", return_value=mock_resp) as mock_get:
            assert connector.test_connection() is True
            mock_get.assert_called_once()

    def test_test_connection_failure(self, connector):
        """test_connection returns False on non-200 response."""
        mock_resp = MagicMock()
        mock_resp.status_code = 401

        with patch("requests.get", return_value=mock_resp) as mock_get:
            assert connector.test_connection() is False

    def test_test_connection_timeout(self, connector):
        """test_connection raises when request raises an exception (no try/except in connector)."""
        with patch("requests.get", side_effect=OSError("connection timeout")):
            with pytest.raises(OSError):
                connector.test_connection()

    # ---- fetch_data ----

    def test_fetch_data_normal_response(self, connector):
        """Normal orders response is parsed and returned as a DataFrame."""
        mock_orders = [
            {
                "name": f"#100{i}",  # distinct order IDs so no grouping collapse
                "email": f"user{i}@example.com",
                "created_at": "2024-01-15T10:00:00Z",
                "total_price": "99.99",
                "referring_site": "https://www.facebook.com",
                "landing_site": "/products/item?utm_source=facebook&fbclid=abc123",
            }
            for i in range(1, 4)
        ]

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"orders": mock_orders}
        mock_resp.headers = {"Link": ""}

        with patch("requests.get", return_value=mock_resp) as mock_get:
            df = connector.fetch_data()
            assert len(df) == 3
            assert "order_id" in df.columns
            assert "revenue" in df.columns

    def test_fetch_data_empty_orders(self, connector):
        """Empty orders list returns an empty DataFrame."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"orders": []}
        mock_resp.headers = {"Link": ""}

        with patch("requests.get", return_value=mock_resp):
            df = connector.fetch_data()
            assert df.empty

    def test_fetch_data_http_error(self, connector):
        """HTTP error raises an exception."""
        mock_resp = MagicMock()
        mock_resp.status_code = 429
        mock_resp.raise_for_status.side_effect = Exception("429 Too Many Requests")

        with patch("requests.get", return_value=mock_resp):
            with pytest.raises(Exception):
                connector.fetch_data()

    def test_fetch_data_pagination_next_page(self, connector):
        """Link header with rel=next paginates correctly across two pages."""
        page1_order = {
            "name": "#1001", "email": "a@b.com",
            "created_at": "2024-01-01T00:00:00Z",
            "total_price": "10.00", "referring_site": "", "landing_site": "",
        }
        page2_order = {
            "name": "#1002", "email": "c@d.com",
            "created_at": "2024-01-02T00:00:00Z",
            "total_price": "20.00", "referring_site": "", "landing_site": "",
        }

        mock_resp1 = MagicMock()
        mock_resp1.status_code = 200
        mock_resp1.json.return_value = {"orders": [page1_order]}
        mock_resp1.headers = {
            "Link": '<https://test-shop.myshopify.com/admin/api/2024-01/orders.json?page=2>; rel="next"'
        }

        mock_resp2 = MagicMock()
        mock_resp2.status_code = 200
        mock_resp2.json.return_value = {"orders": [page2_order]}
        mock_resp2.headers = {"Link": ""}

        with patch("requests.get", side_effect=[mock_resp1, mock_resp2]):
            df = connector.fetch_data()
            assert len(df) == 2

    def test_fetch_data_missing_order_fields(self, connector):
        """Orders missing most fields still parse without crashing."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"orders": [{"name": "#1001"}]}
        mock_resp.headers = {"Link": ""}

        with patch("requests.get", return_value=mock_resp):
            df = connector.fetch_data()
            assert len(df) == 1
            assert "revenue" in df.columns

    def test_fetch_data_with_config(self, connector):
        """ConnectorConfig start/end dates are embedded in request params."""
        from ad_audit.connectors.base import ConnectorConfig
        from datetime import date

        cfg = ConnectorConfig(start_date=date(2024, 1, 1), end_date=date(2024, 1, 31))
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"orders": []}
        mock_resp.headers = {"Link": ""}

        with patch("requests.get", return_value=mock_resp) as mock_get:
            connector.fetch_data(cfg)
            call_kwargs = mock_get.call_args.kwargs
            params = call_kwargs.get("params", {})
            assert "2024-01-01" in str(params.get("created_at_min", ""))
            assert "2024-01-31" in str(params.get("created_at_max", ""))

    def test_fetch_data_extra_fields_ignored(self, connector):
        """Extra fields in order JSON do not break parsing."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "orders": [
                {
                    "name": "#1001",
                    "email": "test@example.com",
                    "created_at": "2024-01-01T00:00:00Z",
                    "total_price": "50.00",
                    "referring_site": "",
                    "landing_site": "",
                    "fulfillment_status": "fulfilled",
                    "note": "some note",
                }
            ]
        }
        mock_resp.headers = {"Link": ""}

        with patch("requests.get", return_value=mock_resp):
            df = connector.fetch_data()
            assert len(df) == 1
            assert df.iloc[0]["order_id"] == "#1001"