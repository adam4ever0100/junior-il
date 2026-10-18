"""How many years of experience does this posting demand?

Three distinctions decide whether the published number is honest:

1. **A range states its floor, not its bar.** "4-8 years" demands four; the
   eight is the top of the band. Reading a range as its maximum would brand
   "0-2 years" — an explicitly junior posting — as closed to juniors.
2. **"A plus" is not a requirement.** "5+ years with Kafka is an advantage"
   must not count, or almost every posting looks shut.
3. **Silence is not zero.** A posting that never mentions experience is
   `years_stated=False`, not `years_min=0`. Conflating those two is the
   easiest way to overstate how open a market is, so they stay separate
   fields and are reported as separate buckets.
"""
import re
from dataclasses import dataclass
from typing import Optional

WORD_NUMBERS = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
}

# A plausible years-of-experience figure. Above this it is a company's age, a
# patent term or a typo, not a hiring requirement.
MAX_PLAUSIBLE_YEARS = 40

# The digit boundaries are load-bearing: without them "100 years" matches as
# "00 years" and yields a threshold of 0, i.e. the steepest possible
# requirement read as no requirement at all.
_NUM = r"(?:(?<!\d)\d{1,2}(?!\d)|" + "|".join(WORD_NUMBERS) + r")"

# "5+ years", "3-5 years", "1–2+ years", "at least 4 years", "minimum 5 years",
# "over 7 years", "8+ years' experience", "4+ year of experience" (sic).
_PATTERN = re.compile(
    rf"""
    (?P<lead>at\s+least\s+|minimum\s+(?:of\s+)?|min\.?\s+|over\s+|
             more\s+than\s+|at\s+minimum\s+)?
    (?P<low>{_NUM})
    \s*(?P<lowplus>\+)?
    (?:\s*(?:-|–|—|to)\s*(?P<high>{_NUM})\s*\+?)?
    \s*(?:years?|yrs?\.?)
    (?:['’]s?)?            # "years' experience"
    """,
    re.IGNORECASE | re.VERBOSE,
)

# Context that demotes a figure from requirement to preference.
# Only phrases that actually make a figure optional. "Ideally" is excluded on
# purpose: in "4+ year of experience ideally in a Customer Success role" it
# qualifies the domain, not the four years, and treating it as a preference
# deleted a real requirement.
PREFERRED_MARKERS = (
    "a plus", "an advantage", "advantageous", "preferred", "preferably",
    "nice to have", "nice-to-have", "bonus", "desirable", "would be great",
    "an asset", "not required",
)

# Context where a number of years is not about the candidate at all:
# "in the last 3 years", "over the past 5 years", "founded 10 years ago".
#
# Every marker here is a full anchored phrase on purpose. An earlier draft used
# bare words like "plan" and "our", which silently matched "3+ years of
# experience planning migrations" and dropped a real requirement. That error
# only ever points one way — it makes the market look more open than it is —
# so these stay narrow, and a missed exclusion (counting a requirement that
# was not one) is the direction to fail in.
NON_REQUIREMENT_MARKERS = (
    "in the last", "in the past", "over the last", "over the past",
    "for the last", "for the past", "within the last", "within the next",
    "in the next", "years ago", "year ago", "year plan", "fiscal year",
    "per year", "a year", "times a year",
)


@dataclass(slots=True)
class YearsFinding:
    threshold: int      # the floor the posting demands
    phrase: str         # what it was read from, for auditing
    required: bool      # False when the context marks it as preferred only


def _to_int(token: str) -> Optional[int]:
    token = token.strip().lower()
    if token.isdigit():
        return int(token)
    return WORD_NUMBERS.get(token)


_PARENTHETICAL = re.compile(r"\([^()]{0,300}\)")


def _line(text: str, start: int, end: int) -> tuple[str, int]:
    """The line the match sits on, plus the match offset within it. Bullets are
    one requirement each, so the line beats a fixed character window."""
    left = text.rfind("\n", 0, start) + 1
    right = text.find("\n", end)
    if right == -1:
        right = len(text)
    return text[left:right], start - left


def _preference_context(line: str, offset: int) -> str:
    """The text whose "a plus" can legitimately demote this figure.

    A parenthetical is its own scope. In the real posting

        6+ years of backend development experience using Java (Go is a plus).

    the "a plus" governs Go, not the six years. Checking the whole line
    demoted the requirement and dropped the role from the experience counts
    altogether — an error that only ever makes the market look more open.
    """
    for match in _PARENTHETICAL.finditer(line):
        if match.start() <= offset < match.end():
            return match.group(0).lower()   # the figure is inside the aside
    return _PARENTHETICAL.sub(" ", line).lower()


def find_all(description: str) -> list[YearsFinding]:
    findings: list[YearsFinding] = []
    if not description:
        return findings
    for match in _PATTERN.finditer(description):
        low = _to_int(match.group("low"))
        if low is None or low > MAX_PLAUSIBLE_YEARS:
            continue
        line, offset = _line(description, match.start(), match.end())
        lowered = line.lower()
        if any(marker in lowered for marker in NON_REQUIREMENT_MARKERS):
            continue
        preference_scope = _preference_context(line, offset)
        required = not any(marker in preference_scope for marker in PREFERRED_MARKERS)
        findings.append(
            YearsFinding(
                threshold=low,
                phrase=match.group(0).strip()[:120],
                required=required,
            )
        )
    return findings


# "Several years of hands-on experience" is a requirement with no number.
# Without this it falls into `stated=False`, which the eligibility rule reads
# as "no experience demanded" — turning a closed door into an open one.
VAGUE_YEARS = re.compile(
    r"(?<!\w)(?:several|multiple|many|numerous|a\s+few|a\s+number\s+of)\s+years?(?!\w)",
    re.IGNORECASE,
)


@dataclass(slots=True)
class YearsSummary:
    stated: bool
    vague: bool              # demands "several years" without a number
    floor: Optional[int]     # gentlest requirement stated anywhere
    bar: Optional[int]       # what a candidate must actually clear
    evidence: Optional[str]


def summarize(description: str) -> YearsSummary:
    """Collapse every stated requirement into the two numbers the index needs.

    `bar` is the steepest requirement, and it is the one that matters: every
    requirement in a posting has to be met, so "7+ years overall, 1+ years
    with Kafka" is a seven-year job, not a one-year job. Published figures use
    `bar`.

    `floor` is the gentlest requirement. It is kept for auditing — a wide gap
    between floor and bar usually means a posting stacked several different
    skills, which is worth being able to look at — but it would understate the
    barrier if it were ever used as the headline.
    """
    vague_match = VAGUE_YEARS.search(description or "")
    required = [f for f in find_all(description) if f.required]
    if not required:
        return YearsSummary(
            stated=False,
            vague=bool(vague_match),
            floor=None,
            bar=None,
            evidence=vague_match.group(0) if vague_match else None,
        )
    thresholds = [f.threshold for f in required]
    steepest = max(required, key=lambda f: f.threshold)
    return YearsSummary(
        stated=True,
        vague=bool(vague_match),
        floor=min(thresholds),
        bar=max(thresholds),
        evidence=steepest.phrase,
    )
