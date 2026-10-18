"""Normalization: raw ATS postings -> the few fields the index depends on.

Kept free of database access on purpose. Every rule in here is a pure function
over strings, so it can be tested against real corpus text without Postgres,
and a rule change is reviewable as a diff rather than a migration.
"""
from junior_il.normalize.core import (
    GRADUATE_YEARS,
    PARSER_VERSION,
    NormalizedPosting,
    normalize_posting,
)

__all__ = [
    "GRADUATE_YEARS",
    "PARSER_VERSION",
    "NormalizedPosting",
    "normalize_posting",
]
