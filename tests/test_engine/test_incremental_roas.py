"""Tests for incremental ROAS computation."""

import pandas as pd

from ad_audit.engine.incremental_roas import compute_incremental_roas
from ad_audit.engine.models import AuditConfig


def test_basic_roas():
    daily = pd.DataFrame({
        "spend": [100, 100, 0, 100],
        "reported_revenue": [500, 500, 0, 500],
        "actual_revenue": [400, 400, 100, 400],
        "actual_conversions": [4, 4, 1, 4],
        "spend_on": [True, True, False, True],
    })
    config = AuditConfig()
    result = compute_incremental_roas(daily, organic_baseline=1.0, config=config)
    assert result.reported_roas > 0
    assert result.true_incremental_roas > 0
    assert result.true_incremental_roas <= result.reported_roas
    assert result.total_spend == 300.0


def test_zero_spend():
    daily = pd.DataFrame({
        "spend": [0, 0],
        "reported_revenue": [0, 0],
        "actual_revenue": [50, 50],
        "actual_conversions": [1, 1],
        "spend_on": [False, False],
    })
    config = AuditConfig()
    result = compute_incremental_roas(daily, organic_baseline=1.0, config=config)
    assert result.reported_roas == 0.0
    assert result.true_incremental_roas == 0.0
