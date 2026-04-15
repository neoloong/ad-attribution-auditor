"""Tests for MetaAdsConnector using mocked HTTP responses."""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch


class TestMetaAdsConnector:
    """Unit tests for MetaAdsConnector with mocked HTTP responses."""

    @pytest.fixture
    def connector(self):
        from ad_audit.connectors.meta_api import MetaAdsConnector

        conn = MetaAdsConnector("act_123456789", "fake_token")
        return conn

    # ---- test_connection ----

    def test_test_connection_success(self, connector):
        """test_connection returns True on HTTP 200."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200

        with patch("requests.get", return_value=mock_resp) as mock_get:
            assert connector.test_connection() is True
            mock_get.assert_called_once()

    def test_test_connection_failure(self, connector):
        """test_connection returns False on non-200 response."""
        mock_resp = MagicMock()
        mock_resp.status_code = 403

        with patch("requests.get", return_value=mock_resp):
            assert connector.test_connection() is False

    def test_test_connection_timeout(self, connector):
        """test_connection raises when request raises an exception (no try/except in connector)."""
        with patch("requests.get", side_effect=OSError("connection timeout")):
            with pytest.raises(OSError):
                connector.test_connection()

    # ---- fetch_data ----

    def test_fetch_data_normal_response(self, connector):
        """Normal insights response is parsed and returned as a DataFrame."""
        mock_body = {
            "data": [
                {
                    "date_start": "2024-01-15",
                    "campaign_name": "Summer Sale",
                    "spend": "150.50",
                    "actions": [{"action_type": "purchase", "value": "5"}],
                    "action_values": [{"action_type": "purchase", "value": "450.00"}],
                }
            ],
            "paging": {"next": None},
        }

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = mock_body

        with patch("requests.get", return_value=mock_resp):
            df = connector.fetch_data()
            assert len(df) == 1
            assert "spend" in df.columns
            assert "reported_conversions" in df.columns

    def test_fetch_data_zero_spend_no_crash(self, connector):
        """Row with zero spend is handled correctly (no divide-by-zero crash)."""
        mock_body = {
            "data": [
                {
                    "date_start": "2024-01-15",
                    "campaign_name": "Inactive Campaign",
                    "spend": "0",
                    "actions": [],
                    "action_values": [],
                }
            ],
            "paging": {"next": None},
        }

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = mock_body

        with patch("requests.get", return_value=mock_resp):
            df = connector.fetch_data()
            assert len(df) == 1
            assert df.iloc[0]["spend"] == 0.0

    def test_fetch_data_empty_data(self, connector):
        """Empty data array returns an empty DataFrame."""
        mock_body = {"data": [], "paging": {"next": None}}

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = mock_body

        with patch("requests.get", return_value=mock_resp):
            df = connector.fetch_data()
            assert df.empty

    def test_fetch_data_pagination(self, connector):
        """Pagination via paging.next URL is followed across two pages."""
        page1 = {
            "data": [
                {
                    "date_start": "2024-01-01", "campaign_name": "A",
                    "spend": "10",
                    "actions": [{"action_type": "purchase", "value": "1"}],
                    "action_values": [{"action_type": "purchase", "value": "30"}],
                }
            ],
            "paging": {"next": "https://graph.facebook.com/v19.0/act_123456789/insights?page=2"},
        }
        page2 = {
            "data": [
                {
                    "date_start": "2024-01-02", "campaign_name": "B",
                    "spend": "20",
                    "actions": [{"action_type": "purchase", "value": "2"}],
                    "action_values": [{"action_type": "purchase", "value": "60"}],
                }
            ],
            "paging": {"next": None},
        }

        mock_resp1 = MagicMock()
        mock_resp1.status_code = 200
        mock_resp1.json.return_value = page1

        mock_resp2 = MagicMock()
        mock_resp2.status_code = 200
        mock_resp2.json.return_value = page2

        with patch("requests.get", side_effect=[mock_resp1, mock_resp2]):
            df = connector.fetch_data()
            assert len(df) == 2

    def test_fetch_data_http_error(self, connector):
        """HTTP error raises an exception."""
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_resp.raise_for_status.side_effect = Exception("500 Server Error")

        with patch("requests.get", return_value=mock_resp):
            with pytest.raises(Exception):
                connector.fetch_data()

    def test_fetch_data_with_config(self, connector):
        """ConnectorConfig start/end dates are embedded in time_range param."""
        from ad_audit.connectors.base import ConnectorConfig
        from datetime import date

        cfg = ConnectorConfig(start_date=date(2024, 2, 1), end_date=date(2024, 2, 28))
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"data": [], "paging": {"next": None}}

        with patch("requests.get", return_value=mock_resp) as mock_get:
            connector.fetch_data(cfg)
            call_kwargs = mock_get.call_args.kwargs
            time_range = call_kwargs.get("params", {}).get("time_range", "")
            assert "2024-02-01" in time_range
            assert "2024-02-28" in time_range

    def test_fetch_data_multiple_actions_purchase(self, connector):
        """Row with multiple action types correctly extracts purchase values."""
        mock_body = {
            "data": [
                {
                    "date_start": "2024-01-15",
                    "campaign_name": "Multi Action",
                    "spend": "100.00",
                    "actions": [
                        {"action_type": "link_click", "value": "500"},
                        {"action_type": "purchase", "value": "3"},
                        {"action_type": "add_to_cart", "value": "12"},
                    ],
                    "action_values": [{"action_type": "purchase", "value": "210.00"}],
                }
            ],
            "paging": {"next": None},
        }

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = mock_body

        with patch("requests.get", return_value=mock_resp):
            df = connector.fetch_data()
            assert len(df) == 1
            assert df.iloc[0]["reported_conversions"] == 3
            assert df.iloc[0]["reported_revenue"] == 210.0