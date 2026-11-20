"""(c) Invalid numeric values are rejected, never coerced to zero."""
from io import BytesIO

import numpy as np
import pandas as pd
import pytest

from ad_audit.ingestion.loader import load_csv
from ad_audit.ingestion.normalizer import (
    normalize_google_ads,
    normalize_gsc,
    normalize_meta_ads,
    normalize_search_terms,
    normalize_shopify_daily,
    normalize_shopify_orders,
    normalize_user_matched,
)
from ad_audit.ingestion.validators import InvalidInputError, validate_schema

META = ("Day,Campaign name,Amount spent (USD),Purchases,Purchase conversion value,Purchase ROAS\n"
        "2026-08-01,Prospecting,100.50,3,300,2.99\n"
        "2026-08-02,Prospecting,{spend},2,200,\n")
GOOGLE = ("Day,Campaign,Cost,Conversions,Conv. value,Cost / conv.\n"
          "2026-08-01,Search - Brand,80.00,4,320,20\n"
          "2026-08-02,Search - Brand,{cost},1.5,60,\n")
SHOPIFY = ("Name,Email,Created at,Total\n"
           "#1001,a@example.com,2026-08-01 10:00:00 -0400,50.00\n"
           "#1002,b@example.com,2026-08-02 11:00:00 -0400,{total}\n")
DAILY = "date,orders,revenue,currency\n2026-08-01,3,150.00,USD\n2026-08-02,{orders},{revenue},USD\n"


def load(text: str) -> pd.DataFrame:
    return load_csv(BytesIO(text.encode("utf-8")))


# Still rejected after the export-token tolerance change (thousands grouping,
# leading currency symbol and accounting negatives are now ACCEPTED in money
# columns -- see test_export_tokens.py).
BAD = ["abc", "N/A", "nan", "inf", "-inf", "--", "1_000", "NULL", "TRUE",
       "12.3.4", "1,2,3", "12,34", "1.234,56", "12.50 \u20ac", "USD 12", "$-5", "-(5)", "$"]


def _assert_rejected(raw, schema, normalizer, column, row_fragment, value):
    check = validate_schema(raw, schema, "upload.csv")
    assert not check.valid
    assert len(check.errors) == 1, check.errors
    msg = check.errors[0]
    assert "upload.csv" in msg
    assert f"column '{column}'" in msg
    assert "data row 2" in msg and row_fragment in msg
    assert value in msg
    with pytest.raises(InvalidInputError) as exc:
        normalizer(raw, source_name="upload.csv")
    assert f"column '{column}'" in str(exc.value) and value in str(exc.value)


@pytest.mark.parametrize("bad", BAD)
def test_meta_invalid_spend_rejected(bad):
    _assert_rejected(load(META.format(spend=bad if "," not in bad else f'"{bad}"')), "meta_ads",
                     normalize_meta_ads, "Amount spent (USD)", "2026-08-02", bad)


@pytest.mark.parametrize("bad", BAD)
def test_google_invalid_cost_rejected(bad):
    _assert_rejected(load(GOOGLE.format(cost=bad if "," not in bad else f'"{bad}"')), "google_ads",
                     normalize_google_ads, "Cost", "2026-08-02", bad)


@pytest.mark.parametrize("bad", BAD)
def test_shopify_orders_invalid_total_rejected(bad):
    _assert_rejected(load(SHOPIFY.format(total=bad if "," not in bad else f'"{bad}"')), "shopify_orders",
                     normalize_shopify_orders, "Total", "#1002", bad)


@pytest.mark.parametrize("bad", BAD)
def test_shopify_daily_invalid_revenue_rejected(bad):
    _assert_rejected(load(DAILY.format(orders=1, revenue=bad if "," not in bad else f'"{bad}"')),
                     "shopify_daily", normalize_shopify_daily, "revenue", "2026-08-02", bad)


@pytest.mark.parametrize("bad", ["two", "inf", "N/A"])
def test_shopify_daily_invalid_orders_rejected(bad):
    _assert_rejected(load(DAILY.format(orders=bad, revenue=10)), "shopify_daily",
                     normalize_shopify_daily, "orders", "2026-08-02", bad)


def test_other_loaders_reject_invalid_numbers():
    gsc = load("Date,Top queries,Clicks,Impressions\n2026-08-01,brand,abc,100\n")
    assert not validate_schema(gsc, "gsc_brand_search", "gsc.csv").valid
    with pytest.raises(InvalidInputError, match="Clicks"):
        normalize_gsc(gsc, "gsc.csv")
    st = load("Search term,Campaign,Cost,Conversions,Impressions,Clicks\nshoes,Brand,--,1,10,2\n")
    with pytest.raises(InvalidInputError, match="Cost"):
        normalize_search_terms(st, "terms.csv")
    um = load("user_id,email_hash,event_type,event_source,timestamp,revenue\n"
              "u1,h,purchase,shopify,2026-08-01T10:00:00,ten\n")
    with pytest.raises(InvalidInputError, match="revenue"):
        normalize_user_matched(um, "users.csv")


# ---------- blank-cell rules ----------

def test_blank_required_numeric_cells_rejected():
    for text, schema, column in [
        (META.format(spend=""), "meta_ads", "Amount spent (USD)"),
        (GOOGLE.format(cost=""), "google_ads", "Cost"),
        (SHOPIFY.format(total=""), "shopify_orders", "Total"),
        (DAILY.format(orders=1, revenue=""), "shopify_daily", "revenue"),
        (DAILY.format(orders="", revenue=0), "shopify_daily", "orders"),
    ]:
        check = validate_schema(load(text), schema, "upload.csv")
        assert not check.valid, schema
        assert f"column '{column}'" in check.errors[0] and "<blank>" in check.errors[0]


def test_blank_optional_platform_columns_follow_documented_rule():
    meta = normalize_meta_ads(load(META.format(spend="50")))
    assert np.isnan(meta.loc[1, "reported_roas"])  # undefined ratio stays NaN
    google = normalize_google_ads(load(GOOGLE.format(cost="10")))
    assert google.loc[1, "reported_revenue"] == 60.0
    assert np.isnan(google.loc[1, "cost_per_conversion"])
    # The NaN ratio is surfaced as a warning, not silently.
    check = validate_schema(load(GOOGLE.format(cost="10")), "google_ads", "google.csv")
    assert check.valid and len(check.warnings) == 1
    assert "Cost / conv." in check.warnings[0] and "data row(s) 2" in check.warnings[0]
    # A blank or marker platform-claimed conversion value is no longer read as
    # 0.0 (it fed reported revenue / reported ROAS / inflation): it rejects.
    for token in ("", "n/a", "--"):
        bad = load(GOOGLE.format(cost="10").replace("1.5,60,", f"1.5,{token},"))
        check = validate_schema(bad, "google_ads", "google.csv")
        assert not check.valid and len(check.errors) == 1
        assert "column 'Conv. value', data row 2" in check.errors[0]
        with pytest.raises(InvalidInputError, match="Conv. value"):
            normalize_google_ads(bad, "google.csv")


def test_shopify_blank_total_allowed_only_on_line_item_continuation_rows():
    ok = load("Name,Email,Created at,Total\n#1,a@x.com,2026-08-01,50\n#1,a@x.com,2026-08-01,\n"
              "#2,b@x.com,2026-08-01,20\n")
    assert validate_schema(ok, "shopify_orders").valid
    out = normalize_shopify_orders(ok).set_index("order_id")
    assert out.loc["#1", "revenue"] == 50.0 and out.loc["#2", "revenue"] == 20.0
    orphan = load("Name,Email,Created at,Total\n#1,a@x.com,2026-08-01,\n#1,a@x.com,2026-08-01,\n")
    check = validate_schema(orphan, "shopify_orders", "orders.csv")
    assert not check.valid and "no other row of this order" in check.errors[0]


def test_signed_shopify_order_totals_are_kept_not_clipped():
    out = normalize_shopify_orders(load(SHOPIFY.format(total="-25.00")))
    assert out.set_index("order_id").loc["#1002", "revenue"] == -25.0
