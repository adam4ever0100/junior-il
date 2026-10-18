"""Hard filters other than experience: degree and security clearance.

These exist because they are the other two reasons a graduate's application is
rejected before a human reads it — and because a clearance requirement is the
difference between a role being theoretically open and actually available.
"""
import re

DEGREE = re.compile(
    r"(?<!\w)(b\.?sc|b\.?a(?!\w)|bachelor'?s?|master'?s?|m\.?sc|phd|ph\.?d|"
    r"degree in|academic degree|תואר)(?!\w)",
    re.IGNORECASE,
)

# A degree mentioned as optional does not filter anyone out.
# Only waivers that replace the degree with something else. A bare "or
# equivalent" is ambiguous — "B.Sc. or equivalent degree" still demands a
# degree — so the waiver has to name experience or say the degree is optional.
DEGREE_OPTIONAL = (
    "or equivalent experience", "or equivalent practical experience",
    "or relevant experience", "or equivalent work experience",
    "degree is a plus", "degree preferred", "no degree",
    "degree not required", "degree is not required",
)

CLEARANCE = re.compile(
    r"(?<!\w)(security clearance|secret clearance|top secret|clearance required|"
    r"סיווג ביטחוני|שירות צבאי|idf service|military service)(?!\w)",
    re.IGNORECASE,
)


def degree_required(description: str) -> bool:
    if not description or not DEGREE.search(description):
        return False
    lowered = description.lower()
    return not any(marker in lowered for marker in DEGREE_OPTIONAL)


def clearance_required(description: str) -> bool:
    return bool(description and CLEARANCE.search(description))
