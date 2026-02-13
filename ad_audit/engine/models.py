"""Core dataclasses for audit configuration and results."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import pandas as pd


class AuditMode(str, Enum):
    AGGREGATE = "aggregate"
    USER_LEVEL = "user_level"


@dataclass
class AuditConfig:
    """Parameters that govern an audit run."""

    mode: AuditMode = AuditMode.AGGREGATE

    # Time-window for click attribution (days)
    attribution_window_days: int = 7

    # Brand-search cannibalization lookback (hours)
    cannibalization_lookback_hours: int = 24

    # Minimum spend to qualify as a "spend-on" day (USD)
    spend_on_threshold: float = 5.0

    # Rolling-window size for Pearson correlation (days)
    correlation_window_days: int = 7

    # Rolling average window for cannibalization scoring (days)
    rolling_avg_days: int = 30


@dataclass
class DeduplicationResult:
    """Overlap between ad-platform-reported conversions and actual e-commerce orders."""

    platform_reported_conversions: int = 0
    actual_conversions: int = 0
    overlap_count: int = 0
    duplication_rate: float = 0.0


@dataclass
class CannibalizationResult:
    """Brand-search cannibalization metrics."""

    cannibalized_days: int = 0
    total_days: int = 0
    cannibalization_score: float = 0.0
    cannibalized_revenue_fraction: float = 0.0


@dataclass
class IncrementalROASResult:
    """Reported vs true incremental ROAS."""

    reported_roas: float = 0.0
    true_incremental_roas: float = 0.0
    inflation_rate: float = 0.0
    total_spend: float = 0.0
    reported_revenue: float = 0.0
    incremental_revenue: float = 0.0


@dataclass
class AuditResult:
    """Full output of an audit run."""

    mode: AuditMode = AuditMode.AGGREGATE
    config: AuditConfig = field(default_factory=AuditConfig)

    # Aggregate metrics
    deduplication: DeduplicationResult = field(
        default_factory=DeduplicationResult
    )
    cannibalization: CannibalizationResult = field(
        default_factory=CannibalizationResult
    )
    incremental_roas: IncrementalROASResult = field(
        default_factory=IncrementalROASResult
    )

    # Time-series correlation
    correlation_mean: float = 0.0
    organic_baseline_conversions: float = 0.0
    incremental_conversions_per_day: float = 0.0

    # Daily merged DataFrame (for charts)
    daily_df: pd.DataFrame | None = None

    # User-level specifics
    total_matched_orders: int = 0
    truly_incremental_orders: int = 0
    cannibalized_orders: int = 0
    user_match_df: pd.DataFrame | None = None

    # Arbitrary extras for extensibility
    extras: dict[str, Any] = field(default_factory=dict)

    @property
    def summary_dict(self) -> dict[str, Any]:
        """Flat dictionary suitable for KPI display."""
        return {
            "mode": self.mode.value,
            "reported_roas": self.incremental_roas.reported_roas,
            "true_incremental_roas": self.incremental_roas.true_incremental_roas,
            "inflation_rate": self.incremental_roas.inflation_rate,
            "duplication_rate": self.deduplication.duplication_rate,
            "cannibalization_score": self.cannibalization.cannibalization_score,
            "organic_baseline_conversions": self.organic_baseline_conversions,
            "incremental_conversions_per_day": self.incremental_conversions_per_day,
            "correlation_mean": self.correlation_mean,
            "total_matched_orders": self.total_matched_orders,
            "truly_incremental_orders": self.truly_incremental_orders,
            "cannibalized_orders": self.cannibalized_orders,
        }
