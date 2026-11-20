"""Joint daily revenue regression with signed campaign effects and 95% CIs.

Revenue = const + sum(b_j * campaign_spend_j) + DOW + trend + error.
Spend columns are scaled for numerical stability; b_j is converted back to
revenue dollars / spend dollar directly, so no estimated-AOV delta method is
needed. HC3 sandwich covariance with t(n-p) critical values gives approximate
heteroskedasticity-robust intervals, conditional on the observed spend panel.
It does not correct endogenous spend, serial correlation, or omitted channels.
GSC remains an overlap diagnostic, not a contemporaneous outcome-derived
control: ads may themselves change search activity.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from scipy.stats import t

from ad_audit.engine.models import CampaignEstimate, IncrementalROASResult
from ad_audit.engine.organic_baseline_regression import _build_features, _durbin_watson


@dataclass
class CampaignModelResult:
    campaigns: list[CampaignEstimate] = field(default_factory=list)
    combined: IncrementalROASResult | None = None
    organic_orders_daily: float | None = None
    incremental_orders_daily: float | None = None
    diagnostics: dict = field(default_factory=dict)


def attach_campaign_spend(daily: pd.DataFrame, ads: pd.DataFrame) -> pd.DataFrame:
    """Retain campaign identity in the daily panel alongside aggregate totals.

    Use platform + campaign_id where all IDs are supplied, otherwise platform
    + campaign_name. Missing campaign-date rows mean zero spend; callers must
    supply complete exports. Unknown campaign identity disables the joint fit.
    """
    daily.attrs["campaigns"] = []
    if ads.empty or "campaign_name" not in ads or ads.campaign_name.isna().any():
        return daily
    ads = ads.copy()
    ads["platform"] = ads.get("platform", pd.Series("unknown", index=ads.index)).fillna("unknown").astype(str)
    use_id = "campaign_id" in ads and ads.campaign_id.notna().all()
    identity = "campaign_id" if use_id else "campaign_name"
    ads[identity] = ads[identity].astype(str)
    for i, ((platform, key), rows) in enumerate(ads.groupby(["platform", identity], sort=True)):
        column = f"campaign_spend_{i}"
        by_date = rows.groupby("date").spend.sum()
        daily[column] = daily.date.map(by_date).fillna(0.0).astype(float)
        daily.attrs["campaigns"].append({
            "column": column, "platform": platform,
            "campaign_name": str(rows.campaign_name.iloc[-1]),
            "campaign_id": key if use_id else None,
            "reported_revenue": float(rows.reported_revenue.sum()),
        })
    return daily


def estimate_campaign_incrementality(daily: pd.DataFrame) -> CampaignModelResult:
    """Fit all campaigns jointly; never emit a campaign point without a CI.

    Refuse short, gapped, nonfinite, rank-deficient or highly ill-conditioned
    panels instead of using a pseudoinverse to invent separate effects.
    Zero-spend campaigns remain unavailable but do not obstruct active ones.
    """
    model = CampaignModelResult()
    metadata = daily.attrs.get("campaigns", [])
    for entry in metadata:
        spend = float(daily[entry["column"]].sum())
        model.campaigns.append(CampaignEstimate(
            platform=entry["platform"], campaign_name=entry["campaign_name"],
            campaign_id=entry["campaign_id"], total_spend=spend,
            reported_roas=entry["reported_revenue"] / spend if spend > 0 else 0.0,
        ))

    def unavailable(reason):
        model.diagnostics.update(status="unavailable", warnings=[reason])
        for campaign in model.campaigns:
            campaign.warnings.append(reason)
        return model

    if not metadata:
        return unavailable("Campaign identity missing; no campaign inference available")
    if len(daily) < 60:
        return unavailable("At least 60 daily observations required for campaign inference")
    if not daily.date.diff().dropna().eq(pd.Timedelta(days=1)).all():
        return unavailable("Daily panel has gaps or duplicate dates; complete exports required")
    active = [i for i, c in enumerate(model.campaigns) if c.total_spend > 0]
    if not active:
        return unavailable("No campaign spend; ROAS is unidentified")

    # Reuse the corrected controls; remove the single total-spend regressor.
    controls, names = _build_features(daily)
    # A parsimonious weekly + linear trend model is used for campaigns.
    # Partial-year month indicators can absorb spend variation and confound
    # calendar steps with trend. The legacy organic helper retains its month
    # controls; they are deliberately not part of this campaign specification.
    keep = [i for i, name in enumerate(names)
            if name != "ad_spend" and not name.startswith("month_")]
    controls = controls[:, keep]
    control_names = [names[i] for i in keep]
    spend = daily[[metadata[i]["column"] for i in active]].to_numpy(dtype=float)
    if not np.isfinite(spend).all() or (spend < 0).any():
        return unavailable("Spend must be finite and nonnegative")
    scales = spend.max(axis=0)
    X = np.column_stack([controls, spend / scales])
    y = daily.actual_revenue.to_numpy(dtype=float)
    n, p = X.shape
    if not np.isfinite(X).all() or not np.isfinite(y).all():
        return unavailable("Nonfinite daily revenue or design")
    if n - p < 10:
        return unavailable("Insufficient residual degrees of freedom")
    try:
        beta, _, rank, singular = np.linalg.lstsq(X, y, rcond=None)
        condition = float(singular[0] / singular[-1]) if singular[-1] > 0 else float("inf")
        if rank < p or condition > 1e8:
            return unavailable("Campaign spend and calendar controls are collinear or ill-conditioned")
        inverse_design = np.linalg.pinv(X)
        residuals = y - X @ beta
        leverage = np.sum(X * inverse_design.T, axis=1)
        if np.any(1 - leverage < 1e-8):
            return unavailable("Unit leverage prevents HC3 uncertainty estimation")
        adjusted = residuals / (1 - leverage)
        sandwich = inverse_design * adjusted
        covariance = sandwich @ sandwich.T
    except np.linalg.LinAlgError:
        return unavailable("Joint OLS decomposition failed")
    critical = float(t.ppf(0.975, n - p))
    warnings = ["Observational association: causal interpretation requires exogenous spend and a valid model"]
    dw = _durbin_watson(residuals)
    if dw < 1.5 or dw > 2.5:
        warnings.append("Residual serial correlation suspected; HC3 intervals do not account for it")
    if not np.isfinite(beta).all() or not np.isfinite(covariance).all():
        return unavailable("Nonfinite coefficient or uncertainty")

    k = controls.shape[1]
    for j, index in enumerate(active):
        campaign = model.campaigns[index]
        effect = float(beta[k + j] / scales[j])
        se = float(np.sqrt(max(0.0, covariance[k + j, k + j])) / scales[j])
        ci = (effect - critical * se, effect + critical * se)
        campaign.true_incremental_roas = effect
        campaign.standard_error = se
        campaign.confidence_interval = ci
        campaign.confidence_level = 0.95
        campaign.incremental_revenue = effect * campaign.total_spend
        campaign.non_incremental = ci[0] <= 0 <= ci[1]
        campaign.status = "estimated"
        campaign.warnings = list(warnings)
    for index in set(range(len(metadata))) - set(active):
        model.campaigns[index].warnings = ["No campaign spend; ROAS is unidentified"]

    # Combined iROAS is a linear contrast of the SAME fit, with full covariance.
    total_spend = float(spend.sum())
    weights = np.zeros(p)
    weights[k:] = spend.sum(axis=0) / scales / total_spend
    effect = float(weights @ beta)
    se = float(np.sqrt(max(0.0, weights @ covariance @ weights)))
    ci = (effect - critical * se, effect + critical * se)
    reported_revenue = float(daily.reported_revenue.sum())
    reported_roas = reported_revenue / total_spend
    inflation = max(0.0, min((reported_roas - effect) / max(reported_roas, 0.01), 10.0))
    model.combined = IncrementalROASResult(
        total_spend=total_spend, reported_revenue=reported_revenue,
        reported_roas=reported_roas, true_incremental_roas=effect,
        incremental_revenue=effect * total_spend, inflation_rate=inflation,
        confidence_interval=ci, confidence_level=0.95, standard_error=se,
        non_incremental=ci[0] <= 0 <= ci[1], estimation_method="joint_revenue_ols_hc3",
    )
    # Order baseline uses the same design, avoiding an AOV approximation.
    order_beta = np.linalg.lstsq(X, daily.actual_conversions.to_numpy(dtype=float), rcond=None)[0]
    model.organic_orders_daily = float(np.mean(controls @ order_beta[:k]))
    model.incremental_orders_daily = float(np.mean((spend / scales) @ order_beta[k:]))
    ss_total = float(np.sum((y - y.mean()) ** 2))
    r2 = 1 - float(residuals @ residuals) / ss_total if ss_total else 0.0
    model.diagnostics = dict(
        status="estimated", method="joint_revenue_ols_hc3", n_obs=n, n_parameters=p,
        residual_df=n-p, r_squared=r2, condition_number=condition,
        durbin_watson=dw, confidence_level=0.95, critical_value=critical,
        controls=control_names, campaigns=metadata, warnings=warnings,
        non_incremental_rule="95% interval includes zero; screening flag, not proof of zero lift",
    )
    return model
