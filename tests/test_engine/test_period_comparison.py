"""Tests for period-over-period comparison."""

import pandas as pd
import numpy as np
import pytest

from ad_audit.engine.period_comparison import compare_periods, MetricDelta
from ad_audit.engine.models import AuditConfig, AuditMode


@pytest.fixture()
def two_period_data():
    """Two periods of ad + shopify data with different characteristics."""
    rng = np.random.default_rng(42)
    dates = pd.date_range("2024-01-01", periods=30, freq="D")
    # Period 1 (first 15 days): moderate spend, good results
    # Period 2 (last 15 days): higher spend, worse results (more duplication)
    spend = np.concatenate([
        rng.uniform(50, 150, size=15),
        rng.uniform(100, 300, size=15),
    ])
    reported_conv = np.concatenate([
        rng.poisson(8, size=15),
        rng.poisson(15, size=15),  # period 2 reports much more
    ])
    revenue = reported_conv * rng.uniform(40, 80, size=30)

    ad_df = pd.DataFrame({
        "date": dates,
        "campaign_name": "Test",
        "spend": spend,
        "reported_conversions": reported_conv,
        "reported_revenue": revenue,
        "reported_roas": np.where(spend > 0, revenue / spend, 0),
        "platform": "meta",
    })

    # Shopify orders: constant organic baseline
    order_rows = []
    for i, dt in enumerate(dates):
        n_orders = rng.poisson(5 if i < 15 else 4)  # slight decrease in period 2
        for j in range(n_orders):
            order_rows.append({
                "order_id": f"#10{i:02d}{j:02d}",
                "date": dt,
                "revenue": float(rng.uniform(30, 100)),
            })
    shopify_df = pd.DataFrame(order_rows)

    return ad_df, shopify_df


def test_compare_periods_basic(two_period_data):
    ad_df, shopify_df = two_period_data
    result = compare_periods(ad_df, shopify_df, "2024-01-16")

    assert result.period_1_label != ""
    assert result.period_2_label != ""
    assert len(result.deltas) > 0

    # Check all expected metrics are present
    metric_names = {d.metric for d in result.deltas}
    assert "reported_roas" in metric_names
    assert "true_incremental_roas" in metric_names
    assert "duplication_rate" in metric_names
    assert "total_spend" in metric_names


def test_compare_periods_root_causes(two_period_data):
    ad_df, shopify_df = two_period_data
    result = compare_periods(ad_df, shopify_df, "2024-01-16")

    assert len(result.root_causes) > 0
    # Should have at least one cause string
    assert all(isinstance(c, str) for c in result.root_causes)


def test_compare_periods_with_gsc(two_period_data):
    ad_df, shopify_df = two_period_data
    dates = pd.date_range("2024-01-01", periods=30, freq="D")
    gsc_df = pd.DataFrame({
        "date": dates,
        "query": "brand",
        "clicks": np.random.default_rng(42).integers(5, 30, size=30),
        "impressions": np.random.default_rng(42).integers(50, 300, size=30),
    })

    result = compare_periods(ad_df, shopify_df, "2024-01-16", gsc_df)
    assert len(result.deltas) > 0
    metric_names = {d.metric for d in result.deltas}
    assert "cannibalization_score" in metric_names


def test_metric_delta_direction():
    d = MetricDelta("test", "Test", 1.0, 2.0, 1.0, 1.0)
    assert d.direction == "increased"

    d2 = MetricDelta("test", "Test", 2.0, 1.0, -1.0, -0.5)
    assert d2.direction == "decreased"

    d3 = MetricDelta("test", "Test", 1.0, 1.0, 0.0, 0.0)
    assert d3.direction == "unchanged"
