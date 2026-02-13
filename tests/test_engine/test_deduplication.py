"""Tests for deduplication module."""

import pandas as pd

from ad_audit.engine.deduplication import compute_deduplication


def test_no_duplication():
    daily = pd.DataFrame({
        "reported_conversions": [5, 5],
        "actual_conversions": [5, 5],
    })
    result = compute_deduplication(daily)
    assert result.duplication_rate == 0.0
    assert result.platform_reported_conversions == 10
    assert result.actual_conversions == 10


def test_duplication_detected():
    daily = pd.DataFrame({
        "reported_conversions": [10, 10],
        "actual_conversions": [5, 5],
    })
    result = compute_deduplication(daily)
    assert result.duplication_rate == 0.5
    assert result.overlap_count == 10


def test_empty():
    daily = pd.DataFrame({
        "reported_conversions": [0],
        "actual_conversions": [0],
    })
    result = compute_deduplication(daily)
    assert result.duplication_rate == 0.0
