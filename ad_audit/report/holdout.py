"""Shared holdout guidance for campaign reports."""

TITLE = "Appendix: Holdout validation design"
ACTION_NOTICE = (
    "The actions below are provisional priorities based on conditional estimates from observational data. "
    "They are not profit decisions. Use the holdout design in the appendix before increasing or cutting budgets."
)

SECTIONS = (
    ("Purpose", "Use a real control to validate incremental revenue for inconclusive campaigns or campaigns "
                "being considered for a budget increase. Test a provisional kill before cutting budget, too."),
    ("Geo holdout", "Split comparable regions into two groups. Maintain delivery in the treatment regions "
                    "and pause or reduce the campaign in the holdout regions."),
    ("Audience or time holdout", "Use platform conversion lift or a randomized PSA or ghost-ad control where "
                                 "supported. Otherwise, alternate full weeks on and off. Promotions, seasonality, "
                                 "changes in demand and carryover can confound a week-on/week-off comparison."),
    ("Holdout size and feasibility", "Start with 10–20% of campaign spend or comparable regions representing "
                                    "that share. A larger holdout generally improves power at a higher opportunity "
                                    "cost. Aggregate exports cannot confirm a viable region split or enough "
                                    "conversion volume. If spend or volume is too low, or regions cannot be split "
                                    "and no audience or time control is viable, holdout is not feasible at the "
                                    "current scale."),
    ("Opportunity cost", "Potential foregone incremental revenue = spend paused during the holdout × the "
                         "campaign's estimated iROAS interval. S_paused is the actual spend withheld over the "
                         "test window. The historical spend shown below is context for planning the share."),
    ("Duration and interpretation", "Allow at least two complete purchase cycles or 2–4 weeks, whichever is "
                                    "longer. If the holdout interval covers the original point estimate, the "
                                    "results are compatible with it. If it excludes the estimate, investigate the "
                                    "discrepancy. If the interval touches or crosses break-even, keep the budget "
                                    "on hold. For a provisional kill, an interval wholly below break-even "
                                    "supports considering a cut. An interval wholly above break-even is a "
                                    "dangerous directional conflict. Maintain budget and investigate before "
                                    "cutting. Apply the same caution before increasing budget if the holdout "
                                    "interval is wholly below break-even."),
)


def cost_example(spend, ci):
    """Substitute the report's numbers, leaving future withheld spend as a variable."""
    if spend is None or spend <= 0:
        return "Holdout is not feasible at the current scale with the available spend data."
    if not ci:
        return f"Reported spend ${spend:,.2f}. The iROAS interval is unavailable for a cost example."
    return f"Reported spend ${spend:,.2f}. Opportunity cost = S_paused × [{ci[0]:.4f}, {ci[1]:.4f}] in dollars."


def appendix_markdown(campaigns):
    lines = [f"## {TITLE}", ""]
    lines.extend(f"**{heading}.** {body}\n" for heading, body in SECTIONS)
    lines.extend(f"- **{name}** — {cost_example(spend, ci)}" for name, spend, ci in campaigns)
    return "\n".join(lines)
