"""Tests for CSV loader."""

from io import BytesIO

import pandas as pd

from ad_audit.ingestion.loader import load_csv


def test_load_csv_from_path(tmp_path):
    csv_path = tmp_path / "test.csv"
    csv_path.write_text("a,b\n1,2\n3,4\n")
    df = load_csv(csv_path)
    assert list(df.columns) == ["a", "b"]
    assert len(df) == 2


def test_load_csv_from_bytes_io():
    buf = BytesIO(b"x,y\n10,20\n")
    df = load_csv(buf)
    assert list(df.columns) == ["x", "y"]
    assert df["x"].iloc[0] == 10


def test_load_csv_utf8_bom():
    content = b"\xef\xbb\xbfcol1,col2\nfoo,bar\n"
    df = load_csv(BytesIO(content))
    assert len(df) == 1
