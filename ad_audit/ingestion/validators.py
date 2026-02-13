"""Schema validation for uploaded DataFrames."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from ad_audit.ingestion.schemas import SCHEMAS, SchemaSpec


@dataclass
class ValidationResult:
    valid: bool
    missing_required: list[str]
    missing_optional: list[str]
    extra_columns: list[str]


def validate_schema(df: pd.DataFrame, schema_name: str) -> ValidationResult:
    """Check that *df* has the required columns for *schema_name*.

    Returns a ``ValidationResult`` with details of any missing columns.
    """
    spec: SchemaSpec = SCHEMAS[schema_name]
    columns = set(df.columns)

    missing_req = sorted(spec.required - columns)
    missing_opt = sorted(spec.optional - columns)
    known = spec.required | spec.optional
    extra = sorted(columns - known)

    return ValidationResult(
        valid=len(missing_req) == 0,
        missing_required=missing_req,
        missing_optional=missing_opt,
        extra_columns=extra,
    )
