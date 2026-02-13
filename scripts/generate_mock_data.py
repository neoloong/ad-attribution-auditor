#!/usr/bin/env python3
"""Generate synthetic sample CSVs for the Ad Attribution Auditor demo.

The generated data models a realistic scenario:
- Ads drive incremental orders on spend-on days (above organic baseline)
- Spend-off days show organic baseline only
- Meta over-reports conversions by ~25-35% (claiming organic orders)
- Google Ads over-reports by ~15-20%
- Brand search clicks spike during spend-off periods (pent-up organic demand)
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "data"
RNG = np.random.default_rng(2024)

# --- Scenario parameters ---
ORGANIC_ORDERS_PER_DAY = 3       # baseline orders that happen without ads
AD_DRIVEN_ORDERS_PER_DAY = 5     # extra orders caused by ads on spend-on days
META_CLAIMED_PER_DAY = 12        # Meta claims ~12 conversions/day (over-reports by claiming organic too)
GOOGLE_CLAIMED_PER_DAY = 8       # Google Ads claims ~8 conversions/day


def generate_meta_ads(days: int = 60) -> pd.DataFrame:
    dates = pd.date_range("2024-01-01", periods=days, freq="D")
    spend = RNG.uniform(50, 300, size=days).round(2)
    # Create spend-off periods (days 10-14, 35-40)
    spend[10:15] = 0
    spend[35:41] = 0

    # Meta over-reports: claims ~12 conv/day (actual ad-driven is only ~5)
    # This includes view-through, 7-day click, and organic orders Meta claims credit for
    inflated_conversions = np.where(
        spend > 0,
        RNG.poisson(META_CLAIMED_PER_DAY, size=days),
        0,
    )

    avg_order_value = RNG.uniform(50, 80, size=days)
    revenue = (inflated_conversions * avg_order_value).round(2)
    with np.errstate(divide="ignore", invalid="ignore"):
        roas = np.where(spend > 0, revenue / spend, 0).round(2)

    campaigns = RNG.choice(
        ["Prospecting - US", "Retargeting - US", "Lookalike - US"],
        size=days,
    )

    return pd.DataFrame({
        "Day": dates.strftime("%Y-%m-%d"),
        "Campaign name": campaigns,
        "Amount spent (USD)": spend,
        "Purchases": inflated_conversions,
        "Purchase conversion value": revenue,
        "Purchase ROAS": roas,
    })


def generate_google_ads(days: int = 60) -> pd.DataFrame:
    """Generate Google Ads data with different spend pattern than Meta."""
    dates = pd.date_range("2024-01-01", periods=days, freq="D")
    spend = RNG.uniform(30, 200, size=days).round(2)
    # Different spend-off pattern (days 5-9, 30-34)
    spend[5:10] = 0
    spend[30:35] = 0

    inflated_conversions = np.where(
        spend > 0,
        RNG.poisson(GOOGLE_CLAIMED_PER_DAY, size=days),
        0,
    )

    avg_order_value = RNG.uniform(40, 75, size=days)
    revenue = (inflated_conversions * avg_order_value).round(2)
    with np.errstate(divide="ignore", invalid="ignore"):
        cost_per_conv = np.where(
            inflated_conversions > 0, spend / inflated_conversions, 0
        ).round(2)

    campaigns = RNG.choice(
        ["Search - Brand", "Search - Non-Brand", "Shopping - US"],
        size=days,
    )

    return pd.DataFrame({
        "Day": dates.strftime("%Y-%m-%d"),
        "Campaign": campaigns,
        "Cost": spend,
        "Conversions": inflated_conversions,
        "Conv. value": revenue,
        "Cost / conv.": cost_per_conv,
    })


def generate_shopify_orders(days: int = 60) -> pd.DataFrame:
    """Generate orders with realistic ad-spend correlation.

    - Spend-on days: organic baseline + ad-driven orders
    - Spend-off days: organic baseline only
    """
    dates = pd.date_range("2024-01-01", periods=days, freq="D")
    spend_off_mask = np.zeros(days, dtype=bool)
    spend_off_mask[10:15] = True
    spend_off_mask[35:41] = True

    # Build per-day order counts
    daily_orders = np.where(
        spend_off_mask,
        RNG.poisson(ORGANIC_ORDERS_PER_DAY, size=days),                           # spend-off: organic only
        RNG.poisson(ORGANIC_ORDERS_PER_DAY + AD_DRIVEN_ORDERS_PER_DAY, size=days), # spend-on: organic + ad-driven
    )

    # Expand into individual order rows
    rows = []
    order_num = 0
    for day_idx, n in enumerate(daily_orders):
        dt = dates[day_idx]
        is_spend_on = not spend_off_mask[day_idx]

        for j in range(n):
            order_num += 1
            # Decide if this order was ad-driven or organic
            if is_spend_on and j >= ORGANIC_ORDERS_PER_DAY:
                # Ad-driven order — mix of Facebook and Google referrals
                if RNG.random() < 0.5:
                    ref = RNG.choice(["https://www.facebook.com/", "https://l.facebook.com/"])
                    landing = f"/collections/all?utm_source=facebook&utm_medium=paid&fbclid=fb{RNG.integers(10000, 99999)}"
                else:
                    ref = "https://www.google.com/"
                    landing = f"/collections/all?utm_source=google&utm_medium=cpc&gclid=gc{RNG.integers(10000, 99999)}"
            elif RNG.random() < 0.3:
                # Some organic orders come from Google
                ref = "https://www.google.com/"
                landing = "/collections/all?utm_source=google&utm_medium=organic"
            else:
                # Direct / other organic
                ref = ""
                landing = "/collections/all"

            ts = dt + pd.Timedelta(seconds=int(RNG.integers(0, 86400)))
            rows.append({
                "Name": f"#1{order_num:04d}",
                "Email": f"customer{RNG.integers(1, 200)}@example.com",
                "Created at": ts.strftime("%Y-%m-%d %H:%M:%S"),
                "Total": round(float(RNG.uniform(25, 180)), 2),
                "Referring Site": ref,
                "Landing Site": landing,
            })

    return pd.DataFrame(rows)


def generate_gsc_brand_search(days: int = 60) -> pd.DataFrame:
    dates = pd.date_range("2024-01-01", periods=days, freq="D")
    spend_off_mask = np.zeros(days, dtype=bool)
    spend_off_mask[10:15] = True
    spend_off_mask[35:41] = True

    base_clicks = 15
    clicks = RNG.poisson(base_clicks, size=days)
    # Brand search spikes during spend-off periods (organic demand persists)
    clicks[spend_off_mask] += RNG.poisson(12, size=spend_off_mask.sum())
    # Also boost on some spend-on days where Meta is cannibalizing
    high_cannibal_days = [5, 6, 7, 25, 26, 27, 50, 51, 52]
    for d in high_cannibal_days:
        if d < days:
            clicks[d] += RNG.integers(8, 15)

    impressions = (clicks * RNG.uniform(8, 15, size=days)).astype(int)

    return pd.DataFrame({
        "Date": dates.strftime("%Y-%m-%d"),
        "Top queries": "mybrand",
        "Clicks": clicks,
        "Impressions": impressions,
    })


def generate_user_matched(n_users: int = 80) -> pd.DataFrame:
    rows: list[dict] = []
    for i in range(n_users):
        uid = f"u{i:04d}"
        email_hash = f"sha256_{RNG.integers(100000, 999999)}"
        base_time = pd.Timestamp("2024-01-05") + pd.Timedelta(hours=int(RNG.integers(0, 1200)))

        # Ad click — mix of Meta and Google Ads
        click_time = base_time
        is_google = i % 4 == 0
        if is_google:
            gclid = f"gc_click_{i:04d}"
            fbclid = ""
            event_source = "google_ads"
        else:
            fbclid = f"fb_click_{i:04d}"
            gclid = ""
            event_source = "meta"

        rows.append({
            "user_id": uid,
            "email_hash": email_hash,
            "event_type": "ad_click",
            "event_source": event_source,
            "timestamp": click_time.isoformat(),
            "revenue": 0,
            "fbclid": fbclid,
            "gclid": gclid,
        })

        # Purchase within attribution window
        purchase_time = click_time + pd.Timedelta(days=int(RNG.integers(1, 7)))
        purchase_rev = round(float(RNG.uniform(20, 180)), 2)
        rows.append({
            "user_id": uid,
            "email_hash": email_hash,
            "event_type": "purchase",
            "event_source": "shopify",
            "timestamp": purchase_time.isoformat(),
            "revenue": purchase_rev,
            "fbclid": fbclid if i % 2 == 0 else "",
            "gclid": gclid if i % 2 == 0 else "",
        })

        # ~40% had brand search before the click (cannibalized)
        if RNG.random() < 0.4:
            search_time = click_time - pd.Timedelta(hours=int(RNG.integers(1, 20)))
            rows.append({
                "user_id": uid,
                "email_hash": email_hash,
                "event_type": "brand_search",
                "event_source": "gsc",
                "timestamp": search_time.isoformat(),
                "revenue": 0,
                "fbclid": "",
                "gclid": "",
            })

    return pd.DataFrame(rows)


def generate_search_terms(n_terms: int = 40) -> pd.DataFrame:
    """Generate a sample Google Ads search term report."""
    brand_terms = ["mybrand", "mybrand shoes", "mybrand sale", "buy mybrand"]
    generic_terms = [
        "running shoes", "best sneakers", "athletic shoes online",
        "shoe sale", "comfortable shoes", "mens shoes", "womens shoes",
        "sports shoes", "casual sneakers", "walking shoes",
        "cheap shoes online", "shoe store near me", "best running shoes 2024",
        "nike alternatives", "adidas competitors", "shoe reviews",
        "waterproof shoes", "hiking boots", "trail running shoes",
        "cross training shoes", "gym shoes", "workout shoes",
        "shoe deals", "discount shoes", "clearance sneakers",
        "leather shoes", "vegan shoes", "eco friendly sneakers",
        "wide fit shoes", "narrow shoes", "arch support shoes",
        "flat feet shoes", "plantar fasciitis shoes", "orthopedic sneakers",
        "slip on shoes", "lace up sneakers",
    ]

    all_terms = brand_terms + generic_terms[:n_terms - len(brand_terms)]

    rows = []
    campaigns = ["Search - Brand", "Search - Non-Brand", "Shopping - US"]
    for term in all_terms:
        is_brand = term in brand_terms
        spend = round(float(RNG.uniform(5, 60 if is_brand else 120)), 2)
        clicks = int(RNG.integers(5, 80 if is_brand else 150))
        impressions = clicks * int(RNG.integers(5, 20))
        # Brand terms get more reported conversions but these may be organic
        conversions = float(RNG.integers(0, 8 if is_brand else 3))
        conv_value = round(conversions * float(RNG.uniform(40, 100)), 2)

        rows.append({
            "Search term": term,
            "Campaign": RNG.choice(campaigns[:1] if is_brand else campaigns[1:]),
            "Cost": spend,
            "Conversions": conversions,
            "Impressions": impressions,
            "Clicks": clicks,
            "Conv. value": conv_value,
            "Ad group": "Auto" if is_brand else "Broad Match",
        })

    return pd.DataFrame(rows)


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    meta = generate_meta_ads()
    meta.to_csv(OUTPUT_DIR / "sample_meta_ads.csv", index=False)
    print(f"  wrote {len(meta)} rows -> data/sample_meta_ads.csv")

    google_ads = generate_google_ads()
    google_ads.to_csv(OUTPUT_DIR / "sample_google_ads.csv", index=False)
    print(f"  wrote {len(google_ads)} rows -> data/sample_google_ads.csv")

    shopify = generate_shopify_orders()
    shopify.to_csv(OUTPUT_DIR / "sample_shopify_orders.csv", index=False)
    print(f"  wrote {len(shopify)} rows -> data/sample_shopify_orders.csv")

    gsc = generate_gsc_brand_search()
    gsc.to_csv(OUTPUT_DIR / "sample_gsc_brand_search.csv", index=False)
    print(f"  wrote {len(gsc)} rows -> data/sample_gsc_brand_search.csv")

    search_terms = generate_search_terms()
    search_terms.to_csv(OUTPUT_DIR / "sample_search_terms.csv", index=False)
    print(f"  wrote {len(search_terms)} rows -> data/sample_search_terms.csv")

    user_matched = generate_user_matched()
    user_matched.to_csv(OUTPUT_DIR / "sample_user_matched.csv", index=False)
    print(f"  wrote {len(user_matched)} rows -> data/sample_user_matched.csv")

    print("\nDone! Sample CSVs written to data/")


if __name__ == "__main__":
    main()
