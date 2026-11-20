"""Real ad-export numeric tokens: accepted forms, missing markers, column shifts.

Accepted (see schemas "Numeric value rules"): quoted thousands grouping in
money and count columns; one leading currency symbol and accounting
negatives in money/ratio columns.  Missing markers (blank, whitespace, --,
-, em/en dash, n/a, N/A) reject money and count columns, and become NaN plus
a validation warning only in unused platform ratio columns.
"""
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


def load(text: str, name: str = "upload.csv") -> pd.DataFrame:
    return load_csv(BytesIO(text.encode("utf-8")), source_name=name)


def q(token: str) -> str:
    """CSV-quote a token (as a real export must when it contains a comma)."""
    return f'"{token}"'


# (token, parsed value) accepted in every money column.
MONEY_OK = [
    ("1,234.56", 1234.56),
    ("1,234", 1234.0),
    ("12,345,678.9", 12345678.9),
    ("$12.00", 12.0),
    ("£12.50", 12.5),
    ("€1,234.50", 1234.5),
    ("-$5", -5.0),
    ("-$1,234.50", -1234.5),
    ("(123.45)", -123.45),
    ("($1,234.50)", -1234.5),
    (" $7 ", 7.0),
    ("42", 42.0),
]
COUNT_OK = [("1,234", 1234.0), ("12,345,678", 12345678.0), ("7", 7.0)]
MISSING = ["", "   ", "--", "-", "—", "–", "n/a", "N/A"]
STILL_INVALID = ["abc", "12.3.4", "1,2,3", "12,34", "nan", "inf", "1.234,56", "12.50 €",
                 "USD 12", "$-5", "-(5)", "(-5)", "$$5", "0,123", "1,234,56"]


def meta_csv(spend="10", purchases="1", value="100", roas="10"):
    return ("Day,Campaign name,Amount spent (USD),Purchases,Purchase conversion value,Purchase ROAS\n"
            "2026-08-01,Prospecting,100.50,3,300,2.99\n"
            f"2026-08-02,Prospecting,{spend},{purchases},{value},{roas}\n")


def google_csv(cost="10", conversions="1", value="100", cpc="10"):
    return ("Day,Campaign,Cost,Conversions,Conv. value,Cost / conv.\n"
            "2026-08-01,Search - Brand,80.00,4,320,20\n"
            f"2026-08-02,Search - Brand,{cost},{conversions},{value},{cpc}\n")


def orders_csv(total="10"):
    return ("Name,Email,Created at,Total\n"
            "#1001,a@example.com,2026-08-01 10:00:00 -0400,50.00\n"
            f"#1002,b@example.com,2026-08-02 11:00:00 -0400,{total}\n")


def daily_csv(orders="1", revenue="10"):
    return f"date,orders,revenue,currency\n2026-08-01,3,150.00,USD\n2026-08-02,{orders},{revenue},USD\n"


def gsc_csv(clicks="5", impressions="50"):
    return f"Date,Top queries,Clicks,Impressions\n2026-08-01,brand,3,30\n2026-08-02,brand,{clicks},{impressions}\n"


def terms_csv(cost="10", conversions="1", impressions="50", clicks="5", value="100"):
    return ("Search term,Campaign,Cost,Conversions,Impressions,Clicks,Conv. value\n"
            "shoes,Brand,1,1,10,2,50\n"
            f"boots,Brand,{cost},{conversions},{impressions},{clicks},{value}\n")


def users_csv(revenue="10"):
    return ("user_id,email_hash,event_type,event_source,timestamp,revenue\n"
            "u1,h1,purchase,shopify,2026-08-01T10:00:00,5\n"
            f"u2,h2,purchase,shopify,2026-08-02T10:00:00,{revenue}\n")


# (schema, normalizer, csv builder, raw column, kwarg, normalized column)
MONEY_COLUMNS = [
    ("meta_ads", normalize_meta_ads, meta_csv, "Amount spent (USD)", "spend", "spend"),
    ("meta_ads", normalize_meta_ads, meta_csv, "Purchase conversion value", "value", "reported_revenue"),
    ("google_ads", normalize_google_ads, google_csv, "Cost", "cost", "spend"),
    ("google_ads", normalize_google_ads, google_csv, "Conv. value", "value", "reported_revenue"),
    ("shopify_orders", normalize_shopify_orders, orders_csv, "Total", "total", "revenue"),
    ("search_terms", normalize_search_terms, terms_csv, "Cost", "cost", "spend"),
    ("search_terms", normalize_search_terms, terms_csv, "Conv. value", "value", "reported_revenue"),
    ("user_matched", normalize_user_matched, users_csv, "revenue", "revenue", "revenue"),
    ("shopify_daily", normalize_shopify_daily, daily_csv, "revenue", "revenue", "revenue"),
]
COUNT_COLUMNS = [
    ("meta_ads", normalize_meta_ads, meta_csv, "Purchases", "purchases", "reported_conversions"),
    ("google_ads", normalize_google_ads, google_csv, "Conversions", "conversions", "reported_conversions"),
    ("shopify_daily", normalize_shopify_daily, daily_csv, "orders", "orders", "orders"),
    ("gsc_brand_search", normalize_gsc, gsc_csv, "Clicks", "clicks", "clicks"),
    ("gsc_brand_search", normalize_gsc, gsc_csv, "Impressions", "impressions", "impressions"),
    ("search_terms", normalize_search_terms, terms_csv, "Conversions", "conversions", "reported_conversions"),
    ("search_terms", normalize_search_terms, terms_csv, "Impressions", "impressions", "impressions"),
    ("search_terms", normalize_search_terms, terms_csv, "Clicks", "clicks", "clicks"),
]
RATIO_COLUMNS = [
    ("meta_ads", normalize_meta_ads, meta_csv, "Purchase ROAS", "roas", "reported_roas"),
    ("google_ads", normalize_google_ads, google_csv, "Cost / conv.", "cpc", "cost_per_conversion"),
]


def _ids(cols):
    return [f"{c[0]}:{c[3]}" for c in cols]


def _row2(out: pd.DataFrame, schema: str, column: str):
    if schema == "shopify_orders":
        return out.set_index("order_id").loc["#1002", column]
    return out[column].iloc[1]


def _assert_one_error(text, schema, normalizer, column, value_fragment, problem=None):
    raw = load(text)
    check = validate_schema(raw, schema, "upload.csv")
    assert not check.valid
    assert len(check.errors) == 1, check.errors
    msg = check.errors[0]
    assert msg.startswith("upload.csv: ")
    assert f"column '{column}', data row 2" in msg
    assert value_fragment in msg
    if problem:
        assert problem in msg
    with pytest.raises(InvalidInputError) as exc:
        normalizer(raw, source_name="upload.csv")
    assert f"column '{column}', data row 2" in str(exc.value)


# ---------- (a) accepted token forms, every loader ----------

@pytest.mark.parametrize("col", MONEY_COLUMNS, ids=_ids(MONEY_COLUMNS))
@pytest.mark.parametrize("token,expected", MONEY_OK)
def test_money_tokens_accepted(col, token, expected):
    schema, normalizer, build, column, kwarg, out_col = col
    if schema == "shopify_daily" and expected < 0:
        # Accounting negatives parse, but the daily gross-revenue gate still rejects them.
        _assert_one_error(build(**{kwarg: q(token)}), schema, normalizer, column, token, "is negative")
        return
    raw = load(build(**{kwarg: q(token)}))
    check = validate_schema(raw, schema, "upload.csv")
    assert check.valid, check.errors
    out = normalizer(raw, source_name="upload.csv")
    assert _row2(out, schema, out_col) == pytest.approx(expected, abs=0, rel=0)


@pytest.mark.parametrize("col", COUNT_COLUMNS, ids=_ids(COUNT_COLUMNS))
@pytest.mark.parametrize("token,expected", COUNT_OK)
def test_count_tokens_accepted(col, token, expected):
    schema, normalizer, build, column, kwarg, out_col = col
    raw = load(build(**{kwarg: q(token)}))
    check = validate_schema(raw, schema, "upload.csv")
    assert check.valid, check.errors
    assert _row2(normalizer(raw, source_name="upload.csv"), schema, out_col) == expected


@pytest.mark.parametrize("col", COUNT_COLUMNS, ids=_ids(COUNT_COLUMNS))
@pytest.mark.parametrize("token", ["$5", "(5)", "€1,234", "-$5"])
def test_count_columns_reject_currency_and_parentheses(col, token):
    schema, normalizer, build, column, kwarg, _ = col
    _assert_one_error(build(**{kwarg: q(token)}), schema, normalizer, column, token,
                      "is not a valid number")


def test_grouped_fraction_in_whole_number_column_still_rejected():
    _assert_one_error(gsc_csv(clicks=q("1,234.5")), "gsc_brand_search", normalize_gsc, "Clicks",
                      "1,234.5", "must be a whole number")


@pytest.mark.parametrize("col", RATIO_COLUMNS, ids=_ids(RATIO_COLUMNS))
@pytest.mark.parametrize("token,expected", [("$1,234.50", 1234.5), ("(2.5)", -2.5), ("2.99", 2.99)])
def test_ratio_tokens_accepted(col, token, expected):
    schema, normalizer, build, column, kwarg, out_col = col
    raw = load(build(**{kwarg: q(token)}))
    assert validate_schema(raw, schema).valid
    assert normalizer(raw)[out_col].iloc[1] == expected


@pytest.mark.parametrize("col", RATIO_COLUMNS, ids=_ids(RATIO_COLUMNS))
@pytest.mark.parametrize("token", MISSING)
def test_missing_marker_in_ratio_column_is_nan_with_warning(col, token):
    schema, normalizer, build, column, kwarg, out_col = col
    raw = load(build(**{kwarg: token}), "ratios.csv")
    check = validate_schema(raw, schema, "ratios.csv")
    assert check.valid and not check.errors
    assert len(check.warnings) == 1
    assert check.warnings[0].startswith(f"ratios.csv: column '{column}': 1 missing cell(s) (data row(s) 2)")
    assert np.isnan(normalizer(raw)[out_col].iloc[1])


def test_clean_file_has_no_warnings():
    assert validate_schema(load(meta_csv()), "meta_ads").warnings == []


def test_currency_symbol_in_utf8_file_is_decoded_as_utf8():
    # chardet alone guesses Windows-1252 for this file and yields "â‚¬12.50".
    raw = load(daily_csv(revenue="€12.50").replace("USD", "EUR"))
    assert raw["revenue"].iloc[1] == "€12.50"
    assert normalize_shopify_daily(raw)["revenue"].iloc[1] == 12.5


# ---------- (b) missing markers in money / count columns reject ----------

@pytest.mark.parametrize("col", MONEY_COLUMNS + COUNT_COLUMNS, ids=_ids(MONEY_COLUMNS + COUNT_COLUMNS))
@pytest.mark.parametrize("token", MISSING)
def test_missing_marker_in_money_or_count_column_rejected(col, token):
    schema, normalizer, build, column, kwarg, _ = col
    shown = "<blank>" if token.strip() == "" else repr(token)
    problem = "is blank" if token.strip() == "" else "is a missing-value marker"
    if schema == "shopify_orders" and token.strip() == "":
        problem = "is blank and no other row of this order has a numeric Total"
    _assert_one_error(build(**{kwarg: token}), schema, normalizer, column, shown, problem)


def test_shopify_total_marker_never_counts_as_line_item_continuation():
    text = ("Name,Email,Created at,Total\n#1,a@x.com,2026-08-01,50\n#1,a@x.com,2026-08-01,--\n")
    check = validate_schema(load(text), "shopify_orders", "orders.csv")
    assert not check.valid and "'--' is a missing-value marker" in check.errors[0]
    # A truly blank continuation row is still allowed (unchanged rule).
    ok = load("Name,Email,Created at,Total\n#1,a@x.com,2026-08-01,\"$1,050.00\"\n#1,a@x.com,2026-08-01,\n")
    assert validate_schema(ok, "shopify_orders").valid
    assert normalize_shopify_orders(ok).set_index("order_id").loc["#1", "revenue"] == 1050.0


def test_missing_conversion_value_no_longer_becomes_zero():
    for build, schema, normalizer, column in [
        (meta_csv, "meta_ads", normalize_meta_ads, "Purchase conversion value"),
        (google_csv, "google_ads", normalize_google_ads, "Conv. value"),
        (terms_csv, "search_terms", normalize_search_terms, "Conv. value"),
    ]:
        _assert_one_error(build(value=""), schema, normalizer, column, "<blank>", "is blank")


# ---------- (c) unquoted thousands separators shift columns ----------

GUIDANCE = "Re-export with quoted numbers or with no thousands separators"


def _assert_field_count_rejection(text, lines):
    with pytest.raises(InvalidInputError) as exc:
        load(text, "google.csv")
    assert len(exc.value.errors) == len(lines), exc.value.errors
    for err, line in zip(exc.value.errors, lines):
        assert err.startswith(f"google.csv: line {line}: ")
        assert GUIDANCE in err


def test_unquoted_thousands_on_every_row_rejected_not_shifted():
    # pandas alone silently made Day the index and shifted every column left.
    _assert_field_count_rejection(
        "Day,Campaign,Cost,Conversions\n2026-08-01,Brand,1,234.50,4\n2026-08-02,Brand,1,100.00,2\n",
        [2, 3])


def test_unquoted_thousands_on_one_row_rejected():
    _assert_field_count_rejection(
        "Day,Campaign,Cost,Conversions\n2026-08-01,Brand,99.00,4\n2026-08-02,Brand,1,234.50,2\n", [3])


def test_short_row_rejected():
    _assert_field_count_rejection("Day,Campaign,Cost,Conversions\n2026-08-01,Brand,5\n", [2])


def test_report_title_lines_above_header_rejected():
    _assert_field_count_rejection(
        "Campaign report\nAugust 1 - 2 2026\nDay,Campaign,Cost,Conversions\n2026-08-01,Brand,5,1\n",
        [3, 4])


def test_quoted_fields_and_blank_lines_do_not_trip_field_count():
    text = ('Day,Campaign,Cost,Conversions\n2026-08-01,"Brand, US",\"1,234.50\",4\n\n'
            '2026-08-02,"multi\nline",5,1\n')
    raw = load(text)
    assert list(raw["Campaign"]) == ["Brand, US", "multi\nline"]
    assert normalize_google_ads(raw)["spend"].tolist() == [1234.5, 5.0]


def test_load_csv_names_path_source(tmp_path):
    path = tmp_path / "meta_export.csv"
    path.write_text("Day,Campaign,Cost,Conversions\n2026-08-01,Brand,1,234,4\n")
    with pytest.raises(InvalidInputError, match=r"^meta_export.csv: line 2: 5 fields but the header has 4"):
        load_csv(path)


# ---------- (d) still-invalid tokens keep today's message ----------

@pytest.mark.parametrize("col", MONEY_COLUMNS, ids=_ids(MONEY_COLUMNS))
@pytest.mark.parametrize("token", STILL_INVALID)
def test_still_invalid_tokens_rejected(col, token):
    schema, normalizer, build, column, kwarg, _ = col
    if token == "inf":
        # pandas itself may read "inf" as float inf ("is not finite") or keep
        # the text ("is not a valid number"); both reject, as before.
        raw = load(build(**{kwarg: q(token)}))
        check = validate_schema(raw, schema, "upload.csv")
        assert len(check.errors) == 1 and f"column '{column}', data row 2" in check.errors[0]
        assert "inf" in check.errors[0]
        return
    _assert_one_error(build(**{kwarg: q(token)}), schema, normalizer, column, repr(token),
                      "is not a valid number")


def test_overflowing_grouped_number_is_not_finite():
    _assert_one_error(meta_csv(spend=q("$" + "1," + ",".join(["000"] * 110))), "meta_ads",
                      normalize_meta_ads, "Amount spent (USD)", "$1,000", "is not finite")


# ---------- gates unchanged ----------

def test_daily_gates_unchanged_with_formatted_tokens():
    dup = "date,orders,revenue,currency\n2026-08-01,1,\"$1,000\",USD\n2026-08-01,2,\"$2,000\",USD\n"
    assert any("duplicate date" in e for e in validate_schema(load(dup), "shopify_daily").errors)
    mixed = "date,orders,revenue,currency\n2026-08-01,1,\"$1,000\",USD\n2026-08-02,2,€2,EUR\n"
    assert any("mixed currencies" in e for e in validate_schema(load(mixed), "shopify_daily").errors)
    zero = "date,orders,revenue,currency\n2026-08-01,0,\"$1,000\",USD\n"
    assert any("orders=0" in e for e in validate_schema(load(zero), "shopify_daily").errors)
