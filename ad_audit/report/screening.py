"""Validate intake Section B and assess risk for report presentation."""

import math


DOWNGRADE_PHRASE = "indistinguishable from demand-following spend"
HIGH_WARNING = (
    "HIGH ENDOGENEITY RISK (budget-behavior screening). Positive conclusions in this report are downgraded: "
    f"they are {DOWNGRADE_PHRASE}. No directional action other than kill is given at this risk level. "
    "Top priority: a controlled holdout."
)
NOT_SCREENED_STATEMENT = (
    "No budget-behavior screening was provided (intake questionnaire Section B), so no endogeneity risk level "
    "was assigned; the standing identification limitations in this report apply in full."
)
LOW_BID_NOTE = "Intraday platform bid allocation exists but budgets are not demand-coupled."
MEDIUM_HOLDOUT_LEAD = (
    "Holdout recommendation (moved forward at this screening risk level): validate the provisional priorities "
    "below with a holdout before increasing or cutting budgets."
)
PLATFORM_BIDDING_TOOLS = {"meta_advantage_plus", "google_smart_bidding"}

_REQUIRED_ENUMS = {
    "b1_setting": ("fixed_monthly", "fixed_adjusted", "fully_dynamic"),
    "b1_frequency": ("rarely_monthly", "weekly", "several_times_week", "daily"),
    "b2_driver": ("sales_roas", "planned_calendar", "other"),
    "b2_lag": ("same_day", "next_day", "within_week", "longer_or_untied", "not_sure"),
    "b3b_promo_changes": ("yes", "no", "not_sure"),
    "b3c_sell_well_add": ("written_rule", "informal_habit", "no", "not_sure"),
}
_REQUIRED_LISTS = {
    "b2_changers": ("person", "predefined_rules", "platform_auto"),
    "b3a_tools": ("meta_rules", "meta_advantage_plus", "google_smart_bidding", "third_party", "none"),
}
_OPTIONAL = {"b4_promotions", "b5_prior_experiment", "b5_lift", "b6_pauses"}


def _check_fields(value, name, required, optional=()):
    if not isinstance(value, dict):
        raise ValueError(f"{name} must be an object")
    missing = required.difference(value)
    if missing:
        raise ValueError(f"{name} is missing required field(s): {', '.join(sorted(missing))}")
    unknown = value.keys() - required.union(optional)
    if unknown:
        raise ValueError(f"{name} has unknown field(s): {', '.join(sorted(map(repr, unknown)))}")


def _check_enum(value, name, choices):
    if not isinstance(value, str) or value not in choices:
        raise ValueError(f"{name} must be one of {', '.join(choices)}; got {value!r}")


def _check_type(value, name, expected):
    if not isinstance(value, expected):
        raise ValueError(f"{name} must be of type {expected.__name__}")


def validate_screening(answers) -> dict:
    """Return validated answers with defaults and independent nested containers."""
    _check_fields(answers, "Section B answers", _REQUIRED_ENUMS.keys() | _REQUIRED_LISTS.keys(), _OPTIONAL)
    normalized = dict(answers)
    for name, choices in _REQUIRED_ENUMS.items():
        _check_enum(answers[name], name, choices)
    for name, choices in _REQUIRED_LISTS.items():
        values = answers[name]
        _check_type(values, name, list)
        for value in values:
            _check_enum(value, name, choices)
        normalized[name] = list(values)

    prior_experiment = answers.get("b5_prior_experiment", "no")
    _check_enum(prior_experiment, "b5_prior_experiment", ("yes", "no", "not_sure"))
    normalized["b5_prior_experiment"] = prior_experiment

    promotions = answers.get("b4_promotions", [])
    _check_type(promotions, "b4_promotions", list)
    for i, promotion in enumerate(promotions):
        name = f"b4_promotions[{i}]"
        _check_fields(promotion, name, {"dates", "event", "budget_raised"})
        _check_type(promotion["dates"], f"{name}.dates", str)
        _check_type(promotion["event"], f"{name}.event", str)
        _check_type(promotion["budget_raised"], f"{name}.budget_raised", bool)
    normalized["b4_promotions"] = [dict(promotion) for promotion in promotions]

    if "b5_lift" in answers:
        lift = answers["b5_lift"]
        _check_fields(lift, "b5_lift", {"scope", "lift", "ci_low", "ci_high"})
        _check_type(lift["scope"], "b5_lift.scope", str)
        for field in ("lift", "ci_low", "ci_high"):
            value = lift[field]
            try:
                finite = type(value) in (int, float) and math.isfinite(value)
            except OverflowError:
                finite = False
            if not finite:
                raise ValueError(f"b5_lift.{field} must be a finite number")
        normalized["b5_lift"] = dict(lift)

    pauses = answers.get("b6_pauses", [])
    _check_type(pauses, "b6_pauses", list)
    for i, pause in enumerate(pauses):
        name = f"b6_pauses[{i}]"
        _check_fields(pause, name, {"campaign", "reason"})
        _check_type(pause["campaign"], f"{name}.campaign", str)
        _check_enum(pause["reason"], f"{name}.reason",
                    ("stockout", "poor_performance", "policy", "planned", "budget_cut", "other"))
    normalized["b6_pauses"] = [dict(pause) for pause in pauses]
    return normalized


def not_screened() -> dict:
    return {"provided": False, "risk_level": None, "basis": [], "not_sure_bump": False,
            "answers": None, "promotions": [], "prior_lift": None}


def assess_screening(answers) -> dict:
    answers = validate_screening(answers)
    promotions = answers["b4_promotions"]
    setting, lag = answers["b1_setting"], answers["b2_lag"]
    sell_well = answers["b3c_sell_well_add"] in ("written_rule", "informal_habit")
    auto_rules = "predefined_rules" in answers["b2_changers"] or "meta_rules" in answers["b3a_tools"]
    fast_lag = lag in ("same_day", "next_day")
    metrics_driven = answers["b2_driver"] == "sales_roas"
    promo_scaling = answers["b3b_promo_changes"] == "yes" or any(p["budget_raised"] for p in promotions)
    coupled = sell_well or auto_rules

    if lag == "same_day" and coupled:
        level = "high"
        reason = "Annex edge rule: same-day changes with automated rules or a sell-well-add rule."
    elif fast_lag and metrics_driven and coupled:
        level = "high"
        reason = "Annex rows 1–2: fast sales/ROAS-driven changes with automated rules or a sell-well-add rule."
    elif (fast_lag and metrics_driven and setting == "fully_dynamic"
          and answers["b1_frequency"] in ("daily", "several_times_week")):
        level = "high"
        reason = "Annex interpretation principle: spend follows demand quickly and systematically."
    elif promo_scaling:
        level = "medium"
        reason = "Annex rows 2–3: promotion-linked changes to budgets, targets or caps."
    elif setting == "fully_dynamic":
        level = "medium"
        reason = "Annex row 4: fully dynamic budgets without a high-risk combination."
    elif fast_lag and metrics_driven:
        level = "medium"
        reason = "Annex signal weighting: fast sales/ROAS-driven changes."
    elif coupled and lag == "within_week":
        level = "medium"
        reason = "Annex signal weighting: weekly changes with automated rules or a sell-well-add rule."
    elif setting in ("fixed_monthly", "fixed_adjusted") and not (fast_lag or coupled or promo_scaling):
        level = "low"
        reason = "Annex rows 5–6: fixed budgets without fast changes, demand-following rules or promotion scaling."
    else:
        level = "medium"
        reason = ("Annex signal weighting fallback for unlisted combinations: fast lag is the top-weighted "
                  "signal, so unlisted fast-lag combinations are not assigned low.")

    basis = [reason]
    bump = lag == "not_sure" or answers["b3c_sell_well_add"] == "not_sure"
    if bump:
        level = {"low": "medium", "medium": "high", "high": "high"}[level]
        basis.append("Annex edge rule: uncertainty about change lag or sell-well-add raises risk one level, up to high.")
    return {"provided": True, "risk_level": level, "basis": basis, "not_sure_bump": bump,
            "answers": answers, "promotions": promotions, "prior_lift": answers.get("b5_lift")}


def presentation_action(action, risk_level):
    if risk_level == "high" and action != "kill":
        return "hold"
    return action


def prior_lift_comparison(prior_lift: dict) -> str:
    return (f"Client's prior lift result for comparison: {prior_lift['scope']}: measured lift "
            f"{prior_lift['lift']:.2f}x, interval [{prior_lift['ci_low']:.2f}, {prior_lift['ci_high']:.2f}]x "
            "— compare with the estimated intervals above.")
