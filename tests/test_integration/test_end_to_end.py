"""End-to-end integration tests: CSV → audit → report."""

from pathlib import Path

import pandas as pd
import pytest

from ad_audit.ingestion.loader import load_csv
from ad_audit.ingestion.validators import validate_schema
from ad_audit.ingestion.normalizer import (
    normalize_meta_ads,
    normalize_google_ads,
    normalize_shopify_orders,
    normalize_gsc,
    normalize_user_matched,
)
from ad_audit.engine.models import AuditConfig, AuditMode
from ad_audit.engine.aggregate_audit import run_aggregate_audit
from ad_audit.engine.user_level_audit import run_user_level_audit
from ad_audit.report.html_export import export_html_report

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"


@pytest.fixture()
def loaded_data():
    """Load and normalize all sample CSVs."""
    meta = normalize_meta_ads(load_csv(DATA_DIR / "sample_meta_ads.csv"))
    google_ads = normalize_google_ads(load_csv(DATA_DIR / "sample_google_ads.csv"))
    shopify = normalize_shopify_orders(load_csv(DATA_DIR / "sample_shopify_orders.csv"))
    gsc = normalize_gsc(load_csv(DATA_DIR / "sample_gsc_brand_search.csv"))
    user = normalize_user_matched(load_csv(DATA_DIR / "sample_user_matched.csv"))
    return meta, google_ads, shopify, gsc, user


class TestAggregateEndToEnd:
    def test_csv_validation(self):
        meta_raw = load_csv(DATA_DIR / "sample_meta_ads.csv")
        result = validate_schema(meta_raw, "meta_ads")
        assert result.valid

        google_raw = load_csv(DATA_DIR / "sample_google_ads.csv")
        result = validate_schema(google_raw, "google_ads")
        assert result.valid

        shopify_raw = load_csv(DATA_DIR / "sample_shopify_orders.csv")
        result = validate_schema(shopify_raw, "shopify_orders")
        assert result.valid

        gsc_raw = load_csv(DATA_DIR / "sample_gsc_brand_search.csv")
        result = validate_schema(gsc_raw, "gsc_brand_search")
        assert result.valid

    def test_full_aggregate_pipeline(self, loaded_data):
        meta, _, shopify, gsc, _ = loaded_data
        config = AuditConfig(mode=AuditMode.AGGREGATE)
        result = run_aggregate_audit(meta, shopify, gsc, config)

        # Basic sanity checks
        assert result.mode == AuditMode.AGGREGATE
        assert result.daily_df is not None
        assert len(result.daily_df) > 0
        assert result.incremental_roas.total_spend > 0
        assert result.incremental_roas.reported_roas > 0
        assert 0 <= result.incremental_roas.inflation_rate <= 1.0
        assert 0 <= result.deduplication.duplication_rate <= 1.0
        assert 0 <= result.cannibalization.cannibalization_score <= 1.0

    def test_aggregate_report_generation(self, loaded_data):
        meta, _, shopify, gsc, _ = loaded_data
        result = run_aggregate_audit(meta, shopify, gsc)
        html = export_html_report(result, ai_summary="Test summary.")
        assert "<html" in html
        assert "Reported ROAS" in html
        assert "Test summary." in html
        assert len(html) > 1000


class TestMultiPlatformEndToEnd:
    def test_meta_plus_google_ads(self, loaded_data):
        """Both Meta + Google Ads combined → full audit."""
        meta, google_ads, shopify, gsc, _ = loaded_data
        ad_df = pd.concat([meta, google_ads], ignore_index=True)
        config = AuditConfig(mode=AuditMode.AGGREGATE)
        result = run_aggregate_audit(ad_df, shopify, gsc, config)

        assert result.mode == AuditMode.AGGREGATE
        assert result.daily_df is not None
        assert result.incremental_roas.total_spend > 0
        assert 0 <= result.deduplication.duplication_rate <= 1.0

    def test_google_ads_only(self, loaded_data):
        """Google Ads only + Shopify → aggregate works."""
        _, google_ads, shopify, gsc, _ = loaded_data
        config = AuditConfig(mode=AuditMode.AGGREGATE)
        result = run_aggregate_audit(google_ads, shopify, gsc, config)

        assert result.mode == AuditMode.AGGREGATE
        assert result.daily_df is not None
        assert result.incremental_roas.total_spend > 0

    def test_multi_platform_report(self, loaded_data):
        """Combined platforms → report generation works."""
        meta, google_ads, shopify, gsc, _ = loaded_data
        ad_df = pd.concat([meta, google_ads], ignore_index=True)
        result = run_aggregate_audit(ad_df, shopify, gsc)
        html = export_html_report(result, ai_summary="Multi-platform test.")
        assert "<html" in html
        assert "Reported ROAS" in html


class TestGracefulDegradation:
    def test_meta_only_no_gsc(self, loaded_data):
        """Meta only + Shopify, no GSC → aggregate works, no cannibalization."""
        meta, _, shopify, _, _ = loaded_data
        config = AuditConfig(mode=AuditMode.AGGREGATE)
        result = run_aggregate_audit(meta, shopify, None, config)

        assert result.mode == AuditMode.AGGREGATE
        assert result.daily_df is not None
        assert "brand_clicks" not in result.daily_df.columns
        assert result.cannibalization.cannibalization_score == 0.0
        assert result.incremental_roas.total_spend > 0

    def test_google_ads_only_no_gsc(self, loaded_data):
        """Google Ads only + Shopify, no GSC → aggregate works."""
        _, google_ads, shopify, _, _ = loaded_data
        config = AuditConfig(mode=AuditMode.AGGREGATE)
        result = run_aggregate_audit(google_ads, shopify, None, config)

        assert result.mode == AuditMode.AGGREGATE
        assert result.daily_df is not None
        assert result.cannibalization.cannibalization_score == 0.0
        assert result.incremental_roas.total_spend > 0

    def test_empty_gsc_dataframe(self, loaded_data):
        """Empty GSC DataFrame treated same as None."""
        meta, _, shopify, _, _ = loaded_data
        empty_gsc = pd.DataFrame({
            "date": pd.Series(dtype="datetime64[ns]"),
            "query": pd.Series(dtype="str"),
            "clicks": pd.Series(dtype="int"),
            "impressions": pd.Series(dtype="int"),
        })
        result = run_aggregate_audit(meta, shopify, empty_gsc)
        assert result.cannibalization.cannibalization_score == 0.0

    def test_no_gsc_report_generation(self, loaded_data):
        """Report generation works without GSC data."""
        meta, _, shopify, _, _ = loaded_data
        result = run_aggregate_audit(meta, shopify, None)
        html = export_html_report(result)
        assert "<html" in html
        assert "Reported ROAS" in html


class TestUserLevelEndToEnd:
    def test_full_user_level_pipeline(self, loaded_data):
        _, _, _, _, user = loaded_data
        config = AuditConfig(mode=AuditMode.USER_LEVEL)
        result = run_user_level_audit(user, config)

        assert result.mode == AuditMode.USER_LEVEL
        assert result.total_matched_orders > 0
        assert result.truly_incremental_orders >= 0
        assert result.cannibalized_orders >= 0

    def test_user_level_report_generation(self, loaded_data):
        _, _, _, _, user = loaded_data
        result = run_user_level_audit(user)
        html = export_html_report(result)
        assert "<html" in html
        assert "Reported ROAS" in html


class TestEdgeCases:
    def test_empty_dataframes(self):
        meta = pd.DataFrame({
            "date": pd.Series(dtype="datetime64[ns]"),
            "campaign_name": pd.Series(dtype="str"),
            "spend": pd.Series(dtype="float"),
            "reported_conversions": pd.Series(dtype="int"),
            "reported_revenue": pd.Series(dtype="float"),
            "reported_roas": pd.Series(dtype="float"),
            "platform": pd.Series(dtype="str"),
        })
        shopify = pd.DataFrame({
            "order_id": pd.Series(dtype="str"),
            "date": pd.Series(dtype="datetime64[ns]"),
            "revenue": pd.Series(dtype="float"),
        })
        result = run_aggregate_audit(meta, shopify, None)
        assert result.incremental_roas.total_spend == 0
        assert result.daily_df is not None

    def test_single_day_data(self):
        meta = pd.DataFrame({
            "date": [pd.Timestamp("2024-01-01")],
            "campaign_name": ["Test"],
            "spend": [100.0],
            "reported_conversions": [5],
            "reported_revenue": [500.0],
            "reported_roas": [5.0],
            "platform": ["meta"],
        })
        shopify = pd.DataFrame({
            "order_id": ["#1001"],
            "date": [pd.Timestamp("2024-01-01")],
            "revenue": [80.0],
        })
        gsc = pd.DataFrame({
            "date": [pd.Timestamp("2024-01-01")],
            "query": ["brand"],
            "clicks": [10],
            "impressions": [100],
        })
        result = run_aggregate_audit(meta, shopify, gsc)
        assert result.daily_df is not None
        assert len(result.daily_df) == 1
