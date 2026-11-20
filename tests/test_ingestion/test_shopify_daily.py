"""Daily Shopify intake (date,orders,revenue,currency) through the production path.

CSV text -> load_csv -> validate_schema -> normalize_* -> run_aggregate_audit.
"""
from io import BytesIO

import numpy as np
import pandas as pd
import pytest

from ad_audit.engine.aggregate_audit import run_aggregate_audit
from ad_audit.ingestion.loader import load_csv
from ad_audit.ingestion.normalizer import (
    normalize_google_ads,
    normalize_meta_ads,
    normalize_shopify_daily,
    normalize_shopify_orders,
)
from ad_audit.ingestion.validators import InvalidInputError, validate_schema

N_DAYS = 90
ZERO_DAYS = (12, 27, 41, 58, 73)  # interior indices forced to verified zero-order days
CAMPAIGNS = [("meta", "Prospecting"), ("meta", "Retargeting"), ("google_ads", "Search - Brand")]


def _csv(df: pd.DataFrame) -> BytesIO:
    return BytesIO(df.to_csv(index=False).encode("utf-8"))


def make_daily_panel(seed=7, n=N_DAYS, zero_days=ZERO_DAYS):
    rng = np.random.default_rng(seed)
    dates = pd.date_range("2026-08-01", periods=n, freq="D")
    spend = np.round(rng.uniform(0, 300, (n, len(CAMPAIGNS))), 2)
    spend[:7] = 0
    lam = 2.0 + np.array([0, 0.3, 0.5, 0.2, 0.8, 1.5, 1.0])[dates.dayofweek] + spend @ [0.02, 0.01, 0.0]
    orders = rng.poisson(lam)
    orders[list(zero_days)] = 0
    revenue = np.round(orders * rng.uniform(40, 60, n), 2)
    daily = pd.DataFrame({
        "date": dates.strftime("%Y-%m-%d"), "orders": orders, "revenue": revenue, "currency": "USD",
    })
    meta_rows, google_rows = [], []
    for j, (platform, name) in enumerate(CAMPAIGNS):
        for i, d in enumerate(dates.strftime("%Y-%m-%d")):
            if platform == "meta":
                meta_rows.append({"Day": d, "Campaign name": name, "Amount spent (USD)": spend[i, j],
                                  "Purchases": 1, "Purchase conversion value": 50.0,
                                  "Purchase ROAS": ""})
            else:
                google_rows.append({"Day": d, "Campaign": name, "Cost": spend[i, j],
                                    "Conversions": 1.5, "Conv. value": 60.0, "Cost / conv.": ""})
    return daily, pd.DataFrame(meta_rows), pd.DataFrame(google_rows)


def load_ads(meta_raw: pd.DataFrame, google_raw: pd.DataFrame) -> pd.DataFrame:
    meta = load_csv(_csv(meta_raw))
    google = load_csv(_csv(google_raw))
    assert validate_schema(meta, "meta_ads", "meta.csv").valid
    assert validate_schema(google, "google_ads", "google.csv").valid
    return pd.concat([normalize_meta_ads(meta, "meta.csv"), normalize_google_ads(google, "google.csv")],
                     ignore_index=True)


def load_daily(daily_raw: pd.DataFrame, name="shopify_daily.csv") -> pd.DataFrame:
    raw = load_csv(_csv(daily_raw))
    check = validate_schema(raw, "shopify_daily", name)
    assert check.valid, check.errors
    return normalize_shopify_daily(raw, name, store_timezone="America/New_York")


# ---------- (a) complete panel with verified zero-order days ----------

def test_complete_daily_panel_with_zero_days_yields_campaign_inference():
    daily_raw, meta_raw, google_raw = make_daily_panel()
    shop = load_daily(daily_raw)
    assert (shop.orders == 0).sum() >= len(ZERO_DAYS)
    result = run_aggregate_audit(load_ads(meta_raw, google_raw), shop)

    diag = result.extras["campaign_model"]
    assert diag["status"] == "estimated", diag
    assert diag["n_obs"] == N_DAYS
    assert result.extras["data_quality_warnings"] == []
    assert result.extras["shopify_granularity"] == "daily"
    # Zero days are rows in the panel, counted as observations, not dropped or filled.
    panel = result.daily_df
    assert len(panel) == N_DAYS
    for i in ZERO_DAYS:
        row = panel.loc[panel.date == pd.Timestamp("2026-08-01") + pd.Timedelta(days=i)]
        assert len(row) == 1
        assert row.actual_conversions.iloc[0] == 0 and row.actual_revenue.iloc[0] == 0
    assert any("verified zero-order day" in n for n in result.extras["data_quality_notes"])
    estimated = [c for c in result.campaign_results if c.status == "estimated"]
    assert len(estimated) == len(CAMPAIGNS)
    for c in estimated:
        lo, hi = c.confidence_interval
        assert np.isfinite(lo) and np.isfinite(hi) and lo < c.true_incremental_roas < hi
    # Endogeneity warning is still attached; calibration does not certify pilots.
    assert any("Observational association" in w for w in diag["warnings"])


def test_same_zero_day_store_as_order_rows_stays_unavailable():
    """The gap this intake closes: order rows cannot prove a zero day."""
    daily_raw, meta_raw, google_raw = make_daily_panel()
    rows = []
    for _, r in daily_raw.iterrows():
        for k in range(int(r.orders)):
            rows.append({"Name": f"#{r.date}-{k}", "Email": f"c{k}@example.com",
                         "Created at": f"{r.date} 12:00:00", "Total": r.revenue / r.orders})
    orders = normalize_shopify_orders(load_csv(_csv(pd.DataFrame(rows))))
    result = run_aggregate_audit(load_ads(meta_raw, google_raw), orders)
    assert result.extras["campaign_model"]["status"] == "unavailable"
    assert "Missing Shopify days" in result.extras["campaign_model"]["warnings"][0]


def test_daily_and_order_level_paths_agree_without_zero_days():
    daily_raw, meta_raw, google_raw = make_daily_panel(zero_days=())
    daily_raw["orders"] = daily_raw["orders"].clip(lower=1)  # every day has an order
    daily_raw["revenue"] = np.where(daily_raw.revenue == 0, 45.0, daily_raw.revenue)
    rows = []
    for _, r in daily_raw.iterrows():
        for k in range(int(r.orders)):
            rows.append({"Name": f"#{r.date}-{k}", "Email": "", "Created at": r.date,
                         "Total": r.revenue if k == 0 else 0.0})
    ads = load_ads(meta_raw, google_raw)
    via_daily = run_aggregate_audit(ads, load_daily(daily_raw))
    via_orders = run_aggregate_audit(ads, normalize_shopify_orders(load_csv(_csv(pd.DataFrame(rows)))))
    assert via_daily.extras["campaign_model"]["status"] == "estimated"
    for a, b in zip(via_daily.campaign_results, via_orders.campaign_results):
        assert a.true_incremental_roas == pytest.approx(b.true_incremental_roas)
        assert a.confidence_interval == pytest.approx(b.confidence_interval)


# ---------- (b) missing interior date ----------

def test_missing_interior_date_makes_campaign_inference_unavailable():
    daily_raw, meta_raw, google_raw = make_daily_panel()
    dropped = daily_raw.date.iloc[45]
    gapped = daily_raw.drop(index=45).reset_index(drop=True)
    shop = load_daily(gapped)  # a gap is not a file-format error ...
    result = run_aggregate_audit(load_ads(meta_raw, google_raw), shop)
    diag = result.extras["campaign_model"]
    assert diag["status"] == "unavailable"  # ... but it blocks campaign inference
    assert dropped in diag["warnings"][0]
    assert "Missing Shopify days inside observed date range (1)" in diag["warnings"][0]
    assert "outside the daily Shopify file" not in diag["warnings"][0]
    assert all(c.status != "estimated" for c in result.campaign_results)
    assert all(c.confidence_interval is None for c in result.campaign_results)


def test_ad_days_outside_daily_panel_are_unobserved_not_zero():
    daily_raw, meta_raw, google_raw = make_daily_panel()
    trimmed = daily_raw.iloc[3:].reset_index(drop=True)  # ads still cover the first 3 days
    result = run_aggregate_audit(load_ads(meta_raw, google_raw), load_daily(trimmed))
    diag = result.extras["campaign_model"]
    assert diag["status"] == "unavailable"
    assert "without a daily Shopify row (3)" in diag["warnings"][0]
    assert "2026-08-01, 2026-08-02, 2026-08-03" in diag["warnings"][0]


def test_non_usd_daily_revenue_with_meta_usd_spend_is_unavailable():
    daily_raw, meta_raw, google_raw = make_daily_panel()
    daily_raw["currency"] = "CAD"
    result = run_aggregate_audit(load_ads(meta_raw, google_raw), load_daily(daily_raw))
    diag = result.extras["campaign_model"]
    assert diag["status"] == "unavailable"
    assert "CAD" in diag["warnings"][0]


# ---------- (d) mixed currency, (e) duplicate date, other contract rules ----------

def _raw(rows):
    return load_csv(_csv(pd.DataFrame(rows, columns=["date", "orders", "revenue", "currency"])))


GOOD = [("2026-08-01", 3, 150.0, "USD"), ("2026-08-02", 0, 0, "USD"), ("2026-08-03", 2, 99.5, "USD")]


def test_three_row_example_with_zero_day_is_valid():
    raw = _raw(GOOD)
    assert validate_schema(raw, "shopify_daily", "daily.csv").valid
    out = normalize_shopify_daily(raw, "daily.csv")
    assert out.orders.tolist() == [3, 0, 2]
    assert out.revenue.tolist() == [150.0, 0.0, 99.5]
    assert out.attrs["currency"] == "USD"


def test_mixed_currency_rejected():
    raw = _raw(GOOD[:2] + [("2026-08-03", 2, 99.5, "EUR")])
    check = validate_schema(raw, "shopify_daily", "daily.csv")
    assert not check.valid
    msg = " ".join(check.errors)
    assert "daily.csv" in msg and "currency" in msg and "mixed currencies" in msg
    assert "USD" in msg and "EUR" in msg
    with pytest.raises(InvalidInputError, match="mixed currencies"):
        normalize_shopify_daily(raw, "daily.csv")


def test_duplicate_date_rejected_not_merged():
    raw = _raw(GOOD + [("2026-08-02", 1, 20.0, "USD")])
    check = validate_schema(raw, "shopify_daily", "daily.csv")
    assert not check.valid
    assert any("duplicate date 2026-08-02" in e and "data row 4" in e and "daily.csv" in e
               for e in check.errors)
    with pytest.raises(InvalidInputError, match="duplicate date"):
        normalize_shopify_daily(raw, "daily.csv")


def test_duplicate_dates_bypassing_validation_still_rejected_by_engine():
    daily_raw, meta_raw, google_raw = make_daily_panel()
    shop = load_daily(daily_raw)
    shop = pd.concat([shop, shop.iloc[[10]]], ignore_index=True)
    with pytest.raises(ValueError, match="Duplicate dates"):
        run_aggregate_audit(load_ads(meta_raw, google_raw), shop)


@pytest.mark.parametrize("row, fragment", [
    (("2026-08-04", 0, 12.0, "USD"), "orders=0"),
    (("2026-08-04", 1, -30.0, "USD"), "is negative"),
    (("2026-08-04", -1, 0, "USD"), "zero or a positive whole number"),
    (("2026-08-04", 2.5, 10, "USD"), "whole number"),
    (("08/04/2026", 1, 10, "USD"), "YYYY-MM-DD"),
    (("2026-08-04T00:00:00-0400", 1, 10, "USD"), "YYYY-MM-DD"),
    (("2026-02-30", 1, 10, "USD"), "YYYY-MM-DD"),
    (("2026-08-04", 1, 10, "usd"), "ISO 4217"),
    (("2026-08-04", 1, 10, ""), "ISO 4217"),
])
def test_daily_contract_violations_rejected(row, fragment):
    raw = _raw(GOOD + [row])
    check = validate_schema(raw, "shopify_daily", "daily.csv")
    assert not check.valid
    assert any(fragment in e and "data row 4" in e for e in check.errors), check.errors


def test_daily_headers_are_exact():
    raw = load_csv(BytesIO(b"Date,Orders,Revenue,Currency\n2026-08-01,1,10,USD\n"))
    assert validate_schema(raw, "shopify_daily").missing_required == ["currency", "date", "orders", "revenue"]
    extra = load_csv(BytesIO(b"date,orders,revenue,currency,refunds\n2026-08-01,1,10,USD,0\n"))
    check = validate_schema(extra, "shopify_daily", "daily.csv")
    assert not check.valid and "unexpected column" in check.errors[0]
