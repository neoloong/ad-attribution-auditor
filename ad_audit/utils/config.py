"""Application-wide configuration defaults."""

from __future__ import annotations

APP_TITLE = "Ad Attribution Auditor"
APP_ICON = "🔍"

# Default OpenAI model for LLM summaries
DEFAULT_LLM_MODEL = "gpt-4o-mini"
DEFAULT_LLM_MAX_TOKENS = 1024
DEFAULT_LLM_TEMPERATURE = 0.3

# Date format expected after normalization
CANONICAL_DATE_FMT = "%Y-%m-%d"

# Attribution defaults
DEFAULT_ATTRIBUTION_WINDOW_DAYS = 7
DEFAULT_CANNIBALIZATION_LOOKBACK_HOURS = 24
DEFAULT_SPEND_ON_THRESHOLD = 5.0
DEFAULT_CORRELATION_WINDOW = 7
DEFAULT_ROLLING_AVG_DAYS = 30
