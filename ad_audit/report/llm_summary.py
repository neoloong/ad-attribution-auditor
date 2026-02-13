"""OpenAI-powered audit summary generation."""

from __future__ import annotations

from ad_audit.engine.models import AuditResult
from ad_audit.utils.config import DEFAULT_LLM_MODEL, DEFAULT_LLM_MAX_TOKENS, DEFAULT_LLM_TEMPERATURE


SYSTEM_PROMPT = """\
You are an expert digital marketing analyst. Given structured audit results comparing \
ad platform reported metrics versus actual e-commerce data, write a clear, actionable \
summary for an e-commerce merchant. Use plain English, avoid jargon, and highlight the most \
important findings. Structure your response with sections: Overview, Key Findings, \
and Recommendations."""


def _detect_platforms(result: AuditResult) -> str:
    """Detect which ad platform(s) are present from the daily DataFrame."""
    if result.daily_df is not None and "platform" in result.daily_df.columns:
        platforms = result.daily_df["platform"].unique()
    else:
        platforms = []

    names = []
    if "meta" in platforms:
        names.append("Meta Ads")
    if "google_ads" in platforms:
        names.append("Google Ads")
    return " and ".join(names) if names else "Ad Platform"


def _build_user_prompt(result: AuditResult) -> str:
    s = result.summary_dict
    ir = result.incremental_roas
    platform_label = _detect_platforms(result)

    prompt = f"""Audit Results Summary:

Ad Platform(s): {platform_label}
Mode: {s['mode']}
Reported ROAS: {s['reported_roas']:.2f}x
True Incremental ROAS: {s['true_incremental_roas']:.2f}x
ROAS Inflation Rate: {s['inflation_rate']:.1%}

Duplication Rate: {s['duplication_rate']:.1%} (platform-reported conversions that exceed actual e-commerce orders)
Cannibalization Score: {s['cannibalization_score']:.1%} (fraction of days where ad platform claims overlap with organic brand search intent)

Total Ad Spend: ${ir.total_spend:,.2f}
Reported Revenue: ${ir.reported_revenue:,.2f}
True Incremental Revenue: ${ir.incremental_revenue:,.2f}

Organic Baseline Conversions per Day: {s['organic_baseline_conversions']:.1f}
Incremental Conversions per Day: {s['incremental_conversions_per_day']:.1f}
Spend-Conversion Correlation: {s['correlation_mean']:.2f}
"""

    if result.total_matched_orders > 0:
        prompt += f"""
User-Level Matching:
Total Matched Orders: {s['total_matched_orders']}
Truly Incremental Orders: {s['truly_incremental_orders']}
Cannibalized Orders: {s['cannibalized_orders']}
"""

    prompt += "\nPlease write a summary report for the merchant."
    return prompt


def generate_summary(
    result: AuditResult,
    api_key: str,
    model: str = DEFAULT_LLM_MODEL,
) -> str:
    """Call OpenAI to produce a natural-language audit summary.

    Returns the summary text (Markdown-formatted).
    """
    from openai import OpenAI

    client = OpenAI(api_key=api_key)

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": _build_user_prompt(result)},
        ],
        max_tokens=DEFAULT_LLM_MAX_TOKENS,
        temperature=DEFAULT_LLM_TEMPERATURE,
    )

    return response.choices[0].message.content or ""
