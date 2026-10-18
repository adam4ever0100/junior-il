"""Turn one raw posting into one normalized row."""
from dataclasses import dataclass
from typing import Any, Optional

from junior_il.normalize import clauses, location, titles, years

# Bump on every change to the rules in this package. Each normalized row and
# each index snapshot stores it, so a number published under one version of
# the rules stays explainable after they change.
PARSER_VERSION = "2026.10.18-1"

# Experience a graduate is assumed to have. One year rather than zero, because
# "1+ years" postings in practice accept a strong graduate and excluding them
# would understate the open door. Stated in METHOD.md.
GRADUATE_YEARS = 1

BLOCKING_SENIORITY = (titles.SENIOR, titles.LEAD, titles.MANAGER)


@dataclass(slots=True)
class NormalizedPosting:
    posting_id: int
    parser_version: str
    is_israel: bool
    il_cities: list[str]
    is_remote: bool
    is_engineering: bool
    seniority: str
    junior_signal: bool
    years_stated: bool
    years_vague: bool
    years_floor: Optional[int]
    years_bar: Optional[int]
    years_evidence: Optional[str]
    degree_required: bool
    clearance_required: bool
    junior_eligible: bool


def normalize_posting(row: dict[str, Any]) -> NormalizedPosting:
    title = row.get("title") or ""
    description = row.get("description") or ""
    department = row.get("department") or ""

    in_israel, cities, remote = location.classify(row.get("location_raw") or "")
    level = titles.seniority(title)
    engineering = titles.is_engineering(title, department)
    experience = years.summarize(description)

    # Every requirement in a posting has to be met, so the steepest one is what
    # closes the door: a single "5+ years" blocks a graduate even when the same
    # posting also says "1+ years of SQL".
    years_ok = not experience.vague and (
        (not experience.stated)
        or (experience.bar is not None and experience.bar <= GRADUATE_YEARS)
    )

    # Deliberately *not* part of this verdict: degree and clearance. Both are
    # recorded and reported separately, because folding them in would make the
    # headline number rest on reading a "military service" mention correctly,
    # and the number has to survive someone arguing with it.
    eligible = (
        in_israel
        and engineering
        and level not in BLOCKING_SENIORITY
        and years_ok
    )

    return NormalizedPosting(
        posting_id=row["id"],
        parser_version=PARSER_VERSION,
        is_israel=in_israel,
        il_cities=cities,
        is_remote=remote,
        is_engineering=engineering,
        seniority=level,
        junior_signal=titles.junior_signal(title),
        years_stated=experience.stated,
        years_vague=experience.vague,
        years_floor=experience.floor,
        years_bar=experience.bar,
        years_evidence=experience.evidence,
        degree_required=clauses.degree_required(description),
        clearance_required=clauses.clearance_required(description),
        junior_eligible=eligible,
    )
