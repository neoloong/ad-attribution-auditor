"""Tests for GoogleAdsConnector using mocked HTTP responses."""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch


class TestGoogleAdsConnector:
    """Unit tests for GoogleAdsConnector with mocked HTTP responses."""

    @pytest.fixture
    def connector(self):
        from ad_audit.connectors.google_ads_api import GoogleAdsConnector

        conn = GoogleAdsConnector(
            customer_id="123-456-7890",
            developer_token="dev_token",
            client_id="client_id",
            client_secret="client_secret",
            refresh_token="refresh_token",
        )
        return conn

    # ---- test_connection ----

    def test_test_connection_success(self, connector):
        """test_connection returns True when customer query returns 200."""
        mock_token_resp = MagicMock()
        mock_token_resp.json.return_value = {"access_token": "access_123"}
        mock_token_resp.raise_for_status = MagicMock()

        mock_search_resp = MagicMock()
        mock_search_resp.status_code = 200

        with patch("requests.post", side_effect=[mock_token_resp, mock_search_resp]):
            assert connector.test_connection() is True

    def test_test_connection_failure(self, connector):
        """test_connection returns False on non-200 response."""
        mock_token_resp = MagicMock()
        mock_token_resp.json.return_value = {"access_token": "access_123"}
        mock_token_resp.raise_for_status = MagicMock()

        mock_search_resp = MagicMock()
        mock_search_resp.status_code = 403

        with patch("requests.post", side_effect=[mock_token_resp, mock_search_resp]):
            assert connector.test_connection() is False

    def test_test_connection_token_refresh_failure(self, connector):
        """test_connection returns False when token refresh fails."""
        mock_token_resp = MagicMock()
        mock_token_resp.status_code = 400
        mock_token_resp.raise_for_status.side_effect = Exception("invalid grant")

        with patch("requests.post", return_value=mock_token_resp):
            assert connector.test_connection() is False

    # ---- fetch_data ----

    def test_fetch_data_normal_response(self, connector):
        """Normal GAQL response is parsed and returned as a DataFrame."""
        mock_token_resp = MagicMock()
        mock_token_resp.json.return_value = {"access_token": "access_123"}
        mock_token_resp.raise_for_status = MagicMock()

        mock_search_resp = MagicMock()
        mock_search_resp.status_code = 200
        mock_search_resp.json.return_value = [
            {
                "results": [
                    {
                        "segments": {"date": "2024-01-15"},
                        "campaign": {"name": "Search Campaign"},
                        "metrics": {
                            "costMicros": "1500000",  # $1.50
                            "conversions": "5",
                            "conversionsValue": "300.00",
                            "costPerConversion": "300000",  # $0.30
                        },
                    }
                ]
            }
        ]
        mock_search_resp.raise_for_status = MagicMock()

        with patch("requests.post", side_effect=[mock_token_resp, mock_search_resp]):
            df = connector.fetch_data()
            assert len(df) == 1
            assert "spend" in df.columns
            assert "reported_conversions" in df.columns

    def test_fetch_data_empty_results(self, connector):
        """Empty results list returns an empty DataFrame."""
        mock_token_resp = MagicMock()
        mock_token_resp.json.return_value = {"access_token": "access_123"}
        mock_token_resp.raise_for_status = MagicMock()

        mock_search_resp = MagicMock()
        mock_search_resp.status_code = 200
        mock_search_resp.json.return_value = [{"results": []}]
        mock_search_resp.raise_for_status = MagicMock()

        with patch("requests.post", side_effect=[mock_token_resp, mock_search_resp]):
            df = connector.fetch_data()
            assert df.empty

    def test_fetch_data_http_error(self, connector):
        """HTTP error raises an exception."""
        mock_token_resp = MagicMock()
        mock_token_resp.json.return_value = {"access_token": "access_123"}
        mock_token_resp.raise_for_status = MagicMock()

        mock_search_resp = MagicMock()
        mock_search_resp.status_code = 429
        mock_search_resp.raise_for_status.side_effect = Exception("429 Rate Limited")

        with patch("requests.post", side_effect=[mock_token_resp, mock_search_resp]):
            with pytest.raises(Exception):
                connector.fetch_data()

    def test_fetch_data_with_config(self, connector):
        """ConnectorConfig start/end dates are embedded in the GAQL query."""
        from ad_audit.connectors.base import ConnectorConfig
        from datetime import date

        cfg = ConnectorConfig(start_date=date(2024, 3, 1), end_date=date(2024, 3, 31))
        mock_token_resp = MagicMock()
        mock_token_resp.json.return_value = {"access_token": "access_123"}
        mock_token_resp.raise_for_status = MagicMock()

        mock_search_resp = MagicMock()
        mock_search_resp.status_code = 200
        mock_search_resp.json.return_value = [{"results": []}]
        mock_search_resp.raise_for_status = MagicMock()

        with patch("requests.post", side_effect=[mock_token_resp, mock_search_resp]) as mock_post:
            connector.fetch_data(cfg)
            # Second call is the searchStream call
            query_body = mock_post.call_args_list[1].kwargs.get("json", {}).get("query", "")
            assert "2024-03-01" in query_body
            assert "2024-03-31" in query_body

    def test_fetch_data_multiple_batches(self, connector):
        """Multiple result batches are all merged into the DataFrame."""
        mock_token_resp = MagicMock()
        mock_token_resp.json.return_value = {"access_token": "access_123"}
        mock_token_resp.raise_for_status = MagicMock()

        mock_search_resp = MagicMock()
        mock_search_resp.status_code = 200
        mock_search_resp.json.return_value = [
            {
                "results": [
                    {
                        "segments": {"date": "2024-01-01"},
                        "campaign": {"name": "Campaign A"},
                        "metrics": {
                            "costMicros": "500000",
                            "conversions": "2",
                            "conversionsValue": "100.00",
                            "costPerConversion": "250000",
                        },
                    }
                ]
            },
            {
                "results": [
                    {
                        "segments": {"date": "2024-01-02"},
                        "campaign": {"name": "Campaign B"},
                        "metrics": {
                            "costMicros": "750000",
                            "conversions": "3",
                            "conversionsValue": "150.00",
                            "costPerConversion": "250000",
                        },
                    }
                ]
            },
        ]
        mock_search_resp.raise_for_status = MagicMock()

        with patch("requests.post", side_effect=[mock_token_resp, mock_search_resp]):
            df = connector.fetch_data()
            assert len(df) == 2

    def test_fetch_data_cost_micros_zero(self, connector):
        """Row with zero costMicros is handled correctly (no divide-by-zero)."""
        mock_token_resp = MagicMock()
        mock_token_resp.json.return_value = {"access_token": "access_123"}
        mock_token_resp.raise_for_status = MagicMock()

        mock_search_resp = MagicMock()
        mock_search_resp.status_code = 200
        mock_search_resp.json.return_value = [
            {
                "results": [
                    {
                        "segments": {"date": "2024-01-01"},
                        "campaign": {"name": "Zero Spend Campaign"},
                        "metrics": {
                            "costMicros": "0",
                            "conversions": "0",
                            "conversionsValue": "0",
                            "costPerConversion": "0",
                        },
                    }
                ]
            }
        ]
        mock_search_resp.raise_for_status = MagicMock()

        with patch("requests.post", side_effect=[mock_token_resp, mock_search_resp]):
            df = connector.fetch_data()
            assert len(df) == 1
            assert df.iloc[0]["spend"] == 0.0

    # ---- fetch_search_terms ----

    def test_fetch_search_terms_normal_response(self, connector):
        """fetch_search_terms parses search term report correctly."""
        mock_token_resp = MagicMock()
        mock_token_resp.json.return_value = {"access_token": "access_123"}
        mock_token_resp.raise_for_status = MagicMock()

        mock_search_resp = MagicMock()
        mock_search_resp.status_code = 200
        mock_search_resp.json.return_value = [
            {
                "results": [
                    {
                        "searchTermView": {"searchTerm": "buy running shoes"},
                        "campaign": {"name": "Brand Campaign"},
                        "adGroup": {"name": "Running Shoes"},
                        "metrics": {
                            "costMicros": "2000000",
                            "conversions": "10",
                            "impressions": "5000",
                            "clicks": "200",
                            "conversionsValue": "500.00",
                        },
                    }
                ]
            }
        ]
        mock_search_resp.raise_for_status = MagicMock()

        with patch("requests.post", side_effect=[mock_token_resp, mock_search_resp]):
            df = connector.fetch_search_terms()
            assert len(df) == 1
            assert "search_term" in df.columns

    def test_fetch_search_terms_empty(self, connector):
        """Empty search term results return an empty DataFrame."""
        mock_token_resp = MagicMock()
        mock_token_resp.json.return_value = {"access_token": "access_123"}
        mock_token_resp.raise_for_status = MagicMock()

        mock_search_resp = MagicMock()
        mock_search_resp.status_code = 200
        mock_search_resp.json.return_value = [{"results": []}]
        mock_search_resp.raise_for_status = MagicMock()

        with patch("requests.post", side_effect=[mock_token_resp, mock_search_resp]):
            df = connector.fetch_search_terms()
            assert df.empty