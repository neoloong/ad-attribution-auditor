"""Shared test fixtures."""

from __future__ import annotations

import datetime as dt

import numpy as np
import pandas as pd
import pytest


@pytest.fixture()
def sample_meta_ads_df() -> pd.DataFrame:
    """Minimal Meta Ads daily report."""
    dates = pd.date_range("2024-01-01", periods=30, freq="D")
    rng = np.random.default_rng(42)
    spend = rng.uniform(0, 200, size=30)
    # Zero-out some days to simulate spend-off periods
    spend[:5] = 0
    spend[15:20] = 0
    purchases = (spend * rng.uniform(0.02, 0.08, size=30)).astype(int)
    revenue = purchases * rng.uniform(30, 80, size=30)
    return pd.DataFrame({
        "date": dates,
        "campaign_name": "Test Campaign",
        "spend": spend,
        "reported_conversions": purchases,
        "reported_revenue": revenue,
        "reported_roas": np.where(spend > 0, np.divide(revenue, spend, where=spend > 0, out=np.zeros_like(revenue)), 0),
        "platform": "meta",
    })


@pytest.fixture()
def sample_google_ads_df() -> pd.DataFrame:
    """Minimal Google Ads daily report."""
    dates = pd.date_range("2024-01-01", periods=30, freq="D")
    rng = np.random.default_rng(99)
    spend = rng.uniform(0, 150, size=30)
    # Different spend-off pattern than Meta
    spend[7:12] = 0
    spend[22:26] = 0
    conversions = (spend * rng.uniform(0.02, 0.06, size=30)).astype(int)
    revenue = conversions * rng.uniform(30, 70, size=30)
    return pd.DataFrame({
        "date": dates,
        "campaign_name": "Google Search Campaign",
        "spend": spend,
        "reported_conversions": conversions,
        "reported_revenue": revenue,
        "reported_roas": np.where(spend > 0, np.divide(revenue, spend, where=spend > 0, out=np.zeros_like(revenue)), 0),
        "platform": "google_ads",
    })


@pytest.fixture()
def sample_shopify_orders_df() -> pd.DataFrame:
    """Minimal Shopify orders."""
    rng = np.random.default_rng(42)
    n = 120
    dates = pd.date_range("2024-01-01", periods=30, freq="D")
    order_dates = rng.choice(dates, size=n)
    return pd.DataFrame({
        "order_id": [f"#10{i:03d}" for i in range(n)],
        "email": [f"user{i}@example.com" for i in range(n)],
        "date": pd.to_datetime(order_dates),
        "revenue": rng.uniform(20, 150, size=n).round(2),
        "referring_site": rng.choice(
            ["https://www.facebook.com", "https://www.google.com", "", None],
            size=n,
        ),
        "landing_site": [
            f"/products/test?utm_source=facebook&fbclid=abc{i}" if i % 3 == 0
            else f"/products/test?utm_source=google" if i % 3 == 1
            else "/products/test"
            for i in range(n)
        ],
    })


@pytest.fixture()
def sample_gsc_df() -> pd.DataFrame:
    """Minimal Google Search Console brand search data."""
    dates = pd.date_range("2024-01-01", periods=30, freq="D")
    rng = np.random.default_rng(42)
    clicks = rng.integers(5, 50, size=30)
    impressions = clicks * rng.integers(5, 20, size=30)
    return pd.DataFrame({
        "date": dates,
        "query": "brand name",
        "clicks": clicks,
        "impressions": impressions,
    })


@pytest.fixture()
def sample_user_matched_df() -> pd.DataFrame:
    """Minimal user-matched events for user-level audit."""
    rng = np.random.default_rng(42)
    rows = []
    for i in range(50):
        email_hash = f"hash_{i:03d}"
        # Ad click event (mix of Meta and Google Ads)
        click_ts = pd.Timestamp("2024-01-10 10:00:00") + pd.Timedelta(hours=i)
        is_google = i % 5 == 0
        rows.append({
            "user_id": f"u{i}",
            "email_hash": email_hash,
            "event_type": "ad_click",
            "event_source": "google_ads" if is_google else "meta",
            "timestamp": click_ts,
            "revenue": 0,
            "fbclid": "" if is_google else f"fb_{i:03d}",
            "gclid": f"gc_{i:03d}" if is_google else "",
        })
        # Purchase event (within attribution window)
        purchase_ts = click_ts + pd.Timedelta(days=rng.integers(1, 6))
        rows.append({
            "user_id": f"u{i}",
            "email_hash": email_hash,
            "event_type": "purchase",
            "event_source": "shopify",
            "timestamp": purchase_ts,
            "revenue": float(rng.uniform(20, 150)),
            "fbclid": f"fb_{i:03d}" if (i % 2 == 0 and not is_google) else "",
            "gclid": f"gc_{i:03d}" if (i % 2 == 0 and is_google) else "",
        })
        # Some users also had a brand search before the click
        if i % 3 == 0:
            search_ts = click_ts - pd.Timedelta(hours=rng.integers(1, 20))
            rows.append({
                "user_id": f"u{i}",
                "email_hash": email_hash,
                "event_type": "brand_search",
                "event_source": "gsc",
                "timestamp": search_ts,
                "revenue": 0,
                "fbclid": "",
                "gclid": "",
            })
    return pd.DataFrame(rows)
