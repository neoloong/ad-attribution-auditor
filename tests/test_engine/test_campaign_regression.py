"""Recovery and refusal checks through the production aggregate entry point."""
import numpy as np
import pandas as pd
import pytest

from ad_audit.engine.aggregate_audit import run_aggregate_audit
from ad_audit.engine.organic_baseline_regression import (
    _build_features, _compute_baseline_from_coeffs, _regression_baseline_full,
)


def make_panel(seed=42, noise=5.0, n=120):
    rng = np.random.default_rng(seed)
    dates = pd.date_range("2026-01-10", periods=n)
    spend = rng.uniform(0, 400, (n, 4))
    spend[:7] = 0
    truth = np.array([4.0, 0.5, 0.0, -0.75])
    organic = 1200 + np.array([0, 25, 60, 30, 80, 160, 90])[dates.dayofweek] + 2 * np.arange(n)
    revenue = organic + spend @ truth + rng.normal(0, noise, n)
    # One variable-value order/day tests direct revenue estimation independently
    # of the gate fixture's constant order values and order-count effects.
    orders = pd.DataFrame({"date": dates, "revenue": revenue})
    ads = pd.concat([pd.DataFrame({
        "date": dates, "campaign_name": f"Campaign {j}", "campaign_id": str(j),
        "platform": "meta" if j == 0 else "google_ads", "spend": spend[:, j],
        "reported_revenue": spend[:, j] * 8, "reported_conversions": 10,
    }) for j in range(4)], ignore_index=True)
    return ads, orders, truth, organic


def by_id(result):
    return {int(c.campaign_id): c for c in result.campaign_results}


def test_recovers_joint_effects_including_negative_and_store_conservation():
    ads, orders, truth, _ = make_panel()
    result = run_aggregate_audit(ads, orders)
    campaigns = by_id(result)
    for j, target in enumerate(truth):
        c = campaigns[j]
        assert c.status == "estimated"
        assert c.true_incremental_roas == pytest.approx(target, abs=0.03)
        assert c.confidence_interval[0] <= target <= c.confidence_interval[1]
        assert c.confidence_level == 0.95
        assert c.standard_error > 0
        assert c.confidence_interval[0] < c.true_incremental_roas < c.confidence_interval[1]
    assert campaigns[2].non_incremental is True
    assert campaigns[3].true_incremental_roas < 0
    assert campaigns[3].confidence_interval[1] < 0
    # Flag is explicitly zero-in-CI, not a synonym for unprofitable/negative.
    assert campaigns[3].non_incremental is False
    total = result.incremental_roas
    assert sum(c.incremental_revenue for c in campaigns.values()) == pytest.approx(total.incremental_revenue)
    assert total.true_incremental_roas == pytest.approx(total.incremental_revenue / total.total_spend)
    weighted_truth = sum(campaigns[j].total_spend * truth[j] for j in range(4)) / total.total_spend
    assert total.confidence_interval[0] <= weighted_truth <= total.confidence_interval[1]


def test_interval_width_responds_to_noise():
    quiet = run_aggregate_audit(*make_panel(noise=5)[:2])
    noisy = run_aggregate_audit(*make_panel(noise=50)[:2])
    for a, b in zip(quiet.campaign_results, noisy.campaign_results):
        assert b.standard_error == pytest.approx(10 * a.standard_error)


def test_claims_utms_gsc_and_row_order_do_not_determine_lift():
    ads, orders, _, _ = make_panel()
    reference = run_aggregate_audit(ads, orders)
    ads["reported_revenue"] *= 100
    ads["reported_conversions"] *= 100
    orders["utm_campaign"] = "Campaign 2"
    gsc = pd.DataFrame({"date": orders.date, "clicks": orders.revenue * 10, "impressions": 1000})
    changed = run_aggregate_audit(ads.sample(frac=1, random_state=9), orders.sample(frac=1, random_state=8), gsc)
    for a, b in zip(reference.campaign_results, changed.campaign_results):
        assert a.true_incremental_roas == pytest.approx(b.true_incremental_roas)
        assert a.confidence_interval == pytest.approx(b.confidence_interval)


def test_collinear_campaigns_refuse_point_estimates():
    ads, orders, _, _ = make_panel()
    ads.loc[ads.campaign_id == "1", "spend"] = ads.loc[ads.campaign_id == "0", "spend"].to_numpy()
    result = run_aggregate_audit(ads, orders)
    assert result.extras["campaign_model"]["status"] == "unavailable"
    for c in result.campaign_results:
        assert c.true_incremental_roas is None and c.confidence_interval is None
        assert c.non_incremental is None
        assert "collinear" in c.warnings[0]
    assert result.incremental_roas.estimation_method == "baseline_subtraction_uncalibrated"
    assert result.incremental_roas.confidence_interval is None


@pytest.mark.parametrize("case", ["short", "gap", "zero"])
def test_unidentifiable_campaigns_have_no_point_or_flag(case):
    ads, orders, _, _ = make_panel(n=30 if case == "short" else 120)
    if case == "gap":
        missing = orders.date.iloc[10]
        ads = ads[ads.date != missing]
        orders = orders[orders.date != missing]
    if case == "zero":
        ads["spend"] = 0
    result = run_aggregate_audit(ads, orders)
    for c in result.campaign_results:
        assert c.status == "unavailable"
        assert c.true_incremental_roas is None
        assert c.confidence_interval is None
        assert c.non_incremental is None


def test_zero_spend_campaign_does_not_prevent_active_inference():
    ads, orders, _, _ = make_panel()
    dormant = ads[ads.campaign_id == "2"].copy()
    dormant["campaign_id"] = "4"
    dormant["spend"] = 0
    result = run_aggregate_audit(pd.concat([ads, dormant]), orders)
    campaigns = by_id(result)
    assert campaigns[4].status == "unavailable"
    assert campaigns[4].true_incremental_roas is None
    assert all(campaigns[i].status == "estimated" for i in range(4))


def test_identity_uses_platform_and_id_instead_of_display_name():
    ads, orders, _, _ = make_panel()
    ads["campaign_name"] = "Same display name"
    result = run_aggregate_audit(ads, orders)
    assert len(result.campaign_results) == 4
    assert all(c.status == "estimated" for c in result.campaign_results)
    # If IDs are unavailable the upload identity is platform + campaign name.
    ads = make_panel()[0].drop(columns="campaign_id")
    ads.loc[ads.campaign_name.isin(["Campaign 0", "Campaign 1"]), "campaign_name"] = "Shared name"
    result = run_aggregate_audit(ads, orders)
    assert len(result.campaign_results) == 4
    assert len([c for c in result.campaign_results if c.campaign_name == "Shared name"]) == 2


def test_no_identity_does_not_invent_campaign_attribution():
    ads, orders, _, _ = make_panel()
    result = run_aggregate_audit(ads.drop(columns=["campaign_name", "campaign_id"]), orders)
    assert result.campaign_results == []
    assert result.extras["campaign_model"]["status"] == "unavailable"


def test_organic_baseline_is_observed_date_counterfactual_with_correct_scaling():
    rng = np.random.default_rng(123)
    dates = pd.date_range("2026-01-17", periods=75)  # unequal DOW/month frequencies
    spend = rng.uniform(0, 400, len(dates))
    spend[:7] = 0
    organic = 30 + dates.dayofweek.to_numpy() * 3 + (dates.month.to_numpy() - 1) * 8 + np.arange(75) * 0.2
    daily = pd.DataFrame({"date": dates, "spend": spend, "actual_conversions": organic + 0.04 * spend})
    X, names = _build_features(daily)
    assert names[0] == "const" and np.all(X[:, 0] == 1)
    beta = np.linalg.lstsq(X, daily.actual_conversions, rcond=None)[0]
    assert _compute_baseline_from_coeffs(beta, names, design=X) == pytest.approx(organic.mean())
    result = _regression_baseline_full(daily)
    assert result.baseline_daily == pytest.approx(organic.mean())
    assert result.ad_marginal_effect == pytest.approx(0.04)
    assert result.r_squared == pytest.approx(1.0)


@pytest.mark.parametrize("remove_ads_too", [False, True])
def test_missing_interior_shopify_day_is_explicit_data_quality_failure(remove_ads_too):
    ads, orders, _, _ = make_panel()
    missing = orders.date.iloc[25]
    orders = orders[orders.date != missing]
    if remove_ads_too:
        ads = ads[ads.date != missing]
    result = run_aggregate_audit(ads, orders)
    assert result.extras['data_quality_warnings']
    warning = result.extras['data_quality_warnings'][0]
    assert 'Missing Shopify days' in warning
    assert missing.strftime('%Y-%m-%d') in warning
    assert 'legacy store totals' in warning
    assert result.incremental_roas.estimation_method == 'baseline_subtraction_uncalibrated'
    assert result.incremental_roas.confidence_interval is None
    for c in result.campaign_results:
        assert c.status == c.effect_label == 'unavailable'
        assert c.true_incremental_roas is c.standard_error is c.confidence_interval is None
        assert warning in c.warnings


def test_complete_shopify_export_has_no_quality_warning_and_exposes_labels():
    result = run_aggregate_audit(*make_panel()[:2])
    assert result.extras['data_quality_warnings'] == []
    cs = by_id(result)
    assert [cs[j].effect_label for j in range(4)] == ['positive', 'positive', 'practically_zero', 'negative']
