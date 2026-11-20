"""User-level audit: email-hash / click-ID matching with time-window joins."""

from __future__ import annotations

import pandas as pd

from ad_audit.engine.models import AuditConfig, AuditMode, AuditResult


def run_user_level_audit(
    user_events_df: pd.DataFrame,
    config: AuditConfig | None = None,
) -> AuditResult:
    """Execute the user-level audit pipeline.

    Parameters
    ----------
    user_events_df : normalized user-matched events DataFrame with columns:
        user_id, email_hash, event_type, event_source, timestamp, revenue, fbclid.
        event_type values: ``ad_click`` (or legacy ``meta_click``), ``purchase``, ``brand_search``.
    config : audit configuration; defaults used if *None*.
    """
    if config is None:
        config = AuditConfig(mode=AuditMode.USER_LEVEL)

    # Accept both "ad_click" (new) and "meta_click" (legacy) event types
    clicks = user_events_df[
        user_events_df["event_type"].isin(["ad_click", "meta_click"])
    ].copy()
    purchases = user_events_df[user_events_df["event_type"] == "purchase"].copy()
    brand_searches = user_events_df[user_events_df["event_type"] == "brand_search"].copy()

    # Step 1: Match purchases to Meta clicks within attribution window
    matched = _match_purchases_to_clicks(clicks, purchases, config)

    # Step 2: Check for prior brand search (cannibalization)
    matched = _check_brand_search_overlap(matched, brand_searches, config)

    # Compute results
    total_matched = len(matched)
    cannibalized = int(matched["is_cannibalized"].sum()) if total_matched > 0 else 0
    truly_incremental = total_matched - cannibalized

    total_revenue = float(matched["revenue"].sum()) if total_matched > 0 else 0.0
    cannibalized_revenue = (
        float(matched.loc[matched["is_cannibalized"], "revenue"].sum())
        if total_matched > 0
        else 0.0
    )
    incremental_revenue = total_revenue - cannibalized_revenue

    # Build ROAS metrics (need total spend from clicks)
    # Approximate: we don't have per-click costs in user-level data,
    # so we report revenue-side metrics only
    from ad_audit.engine.models import (
        DeduplicationResult,
        CannibalizationResult,
        IncrementalROASResult,
    )

    cannibal_score = cannibalized / total_matched if total_matched > 0 else 0.0

    return AuditResult(
        mode=AuditMode.USER_LEVEL,
        config=config,
        deduplication=DeduplicationResult(
            platform_reported_conversions=total_matched,
            actual_conversions=len(purchases),
            overlap_count=total_matched,
            duplication_rate=round(
                max(0.0, 1 - len(purchases) / total_matched) if total_matched > 0 else 0.0,
                4,
            ),
        ),
        cannibalization=CannibalizationResult(
            cannibalized_days=cannibalized,
            total_days=total_matched,
            cannibalization_score=round(cannibal_score, 4),
            cannibalized_revenue_fraction=round(
                cannibalized_revenue / total_revenue if total_revenue > 0 else 0.0, 4
            ),
        ),
        incremental_roas=IncrementalROASResult(
            reported_revenue=round(total_revenue, 2),
            incremental_revenue=round(incremental_revenue, 2),
        ),
        total_matched_orders=total_matched,
        truly_incremental_orders=truly_incremental,
        cannibalized_orders=cannibalized,
        user_match_df=matched,
    )


# ---- internal helpers ----

def _match_purchases_to_clicks(
    clicks: pd.DataFrame,
    purchases: pd.DataFrame,
    config: AuditConfig,
) -> pd.DataFrame:
    """Join purchases to the nearest prior ad click within the attribution window.

    Matching priority:
    1. fbclid / gclid exact match (if both have it)
    2. email_hash match with time-window constraint
    """
    if clicks.empty:
        return pd.DataFrame()
    # Guard against empty DataFrames — return empty result matching the expected schema
    if clicks.empty or purchases.empty:
        return pd.DataFrame(
            columns=[
                "user_id", "email_hash", "timestamp", "revenue",
                "click_time", "time_diff",
            ]
        )

    window = pd.Timedelta(days=config.attribution_window_days)

    # Build click columns list for merge
    click_cols = ["email_hash", "timestamp"]
    if "fbclid" in clicks.columns:
        click_cols.append("fbclid")
    if "gclid" in clicks.columns:
        click_cols.append("gclid")

    rename_map = {"timestamp": "click_time"}
    if "fbclid" in clicks.columns:
        rename_map["fbclid"] = "click_fbclid"
    if "gclid" in clicks.columns:
        rename_map["gclid"] = "click_gclid"

    # Approach: merge on email_hash, then filter by time window
    merged = purchases.merge(
        clicks[click_cols].rename(columns=rename_map),
        on="email_hash",
        how="inner",
    )

    # Keep only rows where purchase happened after click, within window
    merged["time_diff"] = merged["timestamp"] - merged["click_time"]
    merged = merged[
        (merged["time_diff"] >= pd.Timedelta(0))
        & (merged["time_diff"] <= window)
    ]

    # For each purchase, keep the closest click
    if not merged.empty:
        merged = merged.sort_values("time_diff").groupby("user_id").first().reset_index()

    # Also try click-ID matching for unmatched purchases (fbclid + gclid)
    matched_users = set(merged["user_id"]) if not merged.empty else set()
    unmatched_purchases = purchases[~purchases["user_id"].isin(matched_users)]

    for click_id_col in ("fbclid", "gclid"):
        if (
            not unmatched_purchases.empty
            and click_id_col in unmatched_purchases.columns
            and click_id_col in clicks.columns
        ):
            id_match = unmatched_purchases[
                unmatched_purchases[click_id_col].notna()
                & (unmatched_purchases[click_id_col] != "")
            ].merge(
                clicks[[click_id_col, "timestamp"]].rename(
                    columns={"timestamp": "click_time"}
                ),
                on=click_id_col,
                how="inner",
            )
            if not id_match.empty:
                id_match["time_diff"] = id_match["timestamp"] - id_match["click_time"]
                id_match = id_match[
                    (id_match["time_diff"] >= pd.Timedelta(0))
                    & (id_match["time_diff"] <= window)
                ]
                if not id_match.empty:
                    id_match = (
                        id_match.sort_values("time_diff")
                        .groupby("user_id")
                        .first()
                        .reset_index()
                    )
                    merged = pd.concat([merged, id_match], ignore_index=True)
                    matched_users.update(id_match["user_id"])
                    unmatched_purchases = purchases[
                        ~purchases["user_id"].isin(matched_users)
                    ]

    return merged


def _check_brand_search_overlap(
    matched: pd.DataFrame,
    brand_searches: pd.DataFrame,
    config: AuditConfig,
) -> pd.DataFrame:
    """Flag matched orders where user had a brand search before the click."""
    if matched.empty or brand_searches.empty:
        matched["is_cannibalized"] = False
        return matched

    lookback = pd.Timedelta(hours=config.cannibalization_lookback_hours)

    # Merge matched with brand searches on email_hash
    check = matched.merge(
        brand_searches[["email_hash", "timestamp"]].rename(
            columns={"timestamp": "search_time"}
        ),
        on="email_hash",
        how="left",
    )

    # Brand search must be before the click, within lookback window
    check["search_before_click"] = (
        check["search_time"].notna()
        & (check["click_time"] - check["search_time"] >= pd.Timedelta(0))
        & (check["click_time"] - check["search_time"] <= lookback)
    )

    # Aggregate: if any brand search qualifies, mark as cannibalized
    cannibalized_users = set(
        check.loc[check["search_before_click"], "user_id"]
    )

    matched["is_cannibalized"] = matched["user_id"].isin(cannibalized_users)
    return matched
