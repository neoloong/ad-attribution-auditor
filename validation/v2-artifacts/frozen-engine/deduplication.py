"""Deduplication: compare ad-platform-reported conversions vs actual e-commerce orders."""

from __future__ import annotations

import pandas as pd

from ad_audit.engine.models import DeduplicationResult


def compute_deduplication(daily: pd.DataFrame) -> DeduplicationResult:
    """Compare aggregate platform-reported conversions with actual orders.

    Parameters
    ----------
    daily : merged daily DataFrame with ``reported_conversions`` and ``actual_conversions``.
    """
    platform_total = int(daily["reported_conversions"].sum())
    actual_total = int(daily["actual_conversions"].sum())

    if platform_total == 0 and actual_total == 0:
        return DeduplicationResult()

    # Overlap: daily min(reported, actual) – proxy for how many platform claims
    # are backed by a real order on the same day.
    overlap = int(daily[["reported_conversions", "actual_conversions"]].min(axis=1).sum())

    # Duplication rate: fraction of platform-reported that exceed actual
    excess = max(0, platform_total - actual_total)
    dup_rate = excess / platform_total if platform_total > 0 else 0.0

    return DeduplicationResult(
        platform_reported_conversions=platform_total,
        actual_conversions=actual_total,
        overlap_count=overlap,
        duplication_rate=round(dup_rate, 4),
    )
