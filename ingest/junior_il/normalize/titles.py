"""What kind of role is this, and is it aimed at someone starting out?

Titles carry the signal here, not departments. The corpus shows why: Israeli
R&D postings arrive under "R&D", "Engineering", "CX - R&D Engineering",
"Development", "Products and AI R&D", "Engineering - SSE" and "VM, Public
Safety", while plenty of non-engineering roles sit under "R&D" too. Department
is kept as a weak supporting signal only.
"""
import re

JUNIOR = "junior"
MID = "mid"
SENIOR = "senior"
LEAD = "lead"
MANAGER = "manager"
UNSPECIFIED = "unspecified"


def _words(*alternatives: str) -> re.Pattern[str]:
    """Word-boundary alternation. The boundary is not optional: without it
    "Intern" matches "Director of AI Engineering, Internal Products", which is
    a real posting in this corpus and not an internship."""
    joined = "|".join(alternatives)
    return re.compile(rf"(?<!\w)(?:{joined})(?!\w)", re.IGNORECASE)


# Ordered most senior first: a "Senior Engineering Manager" is a manager.
SENIORITY_RULES: tuple[tuple[str, re.Pattern[str] | None], ...] = (
    (MANAGER, _words(
        "manager", "director", "head", "vp", "vice president", "chief",
        "cto", "cio", "ceo", "svp", "evp", "gm", "general manager",
        "מנהל", "מנהלת",
    )),
    (LEAD, _words("lead", "leader", "tech lead", "team lead", "tl")),
    (SENIOR, _words(
        "senior", "sr", "snr", "staff", "principal", "distinguished",
        "expert", "architect", "fellow", "בכיר",
    )),
    (JUNIOR, None),   # filled in below; the pattern is also used on its own
)

# Named rather than reached for by index, because this one is also the public
# "the title itself says junior" signal.
JUNIOR_SIGNAL = _words(
    "junior", "jr", "graduate", "grad", "new grad", "entry level",
    "entry-level", "intern", "internship", "student", "trainee",
    "apprentice", "ג'וניור", "סטודנט", "סטודנטית", "מתמחה", "מתמחת",
)

SENIORITY_RULES = tuple(
    (level, JUNIOR_SIGNAL if pattern is None else pattern)
    for level, pattern in SENIORITY_RULES
)

# "Builds software" — deliberately narrower than "technical". Deciding where QA
# sits matters: QA, automation and SDET roles are in, because they are
# engineering jobs and they are one of the few doors in this market that opens
# to a graduate at all.
ENGINEERING = _words(
    "engineer", "engineering", "developer", "development", "programmer",
    "software", "backend", "back end", "back-end", "frontend", "front end",
    "front-end", "fullstack", "full stack", "full-stack", "devops", "sre",
    "site reliability", "infrastructure", "platform", "embedded", "firmware",
    "algorithm", "algorithms", "data engineer", "data scientist", "machine learning",
    "ml", "ai", "nlp", "computer vision", "qa", "sdet", "automation",
    "test", "tester", "testing", "mobile", "android", "ios", "web",
    "security researcher", "malware", "reverse engineering", "cloud",
    "database", "dba", "sysadmin", "system administrator", "r&d",
    "מפתח", "מפתחת", "מתכנת", "בודק", "בודקת",
)

# Titles that contain an engineering word but are not software-building jobs.
# "Sales Engineer" and "Solutions Engineer" are customer-facing; excluding them
# is a judgement call, and it is recorded in METHOD.md rather than buried here.
NOT_ENGINEERING = _words(
    "sales", "presales", "pre-sales", "account executive", "account manager",
    "customer success", "business development", "bdr", "sdr", "marketing",
    "recruiter", "recruiting", "talent", "people", "hr", "finance",
    "accountant", "legal", "counsel", "procurement", "office",
    "employer branding", "content writer", "copywriter", "designer",
    "product manager", "project manager", "program manager", "scrum",
    "customer support", "technical support", "support engineer",
    "solutions engineer", "solution engineer", "solutions architect",
    "field operations", "operations manager", "trainer", "instructor",
)


def seniority(title: str) -> str:
    for level, pattern in SENIORITY_RULES:
        if pattern.search(title or ""):
            return level
    return UNSPECIFIED


def junior_signal(title: str) -> bool:
    return bool(JUNIOR_SIGNAL.search(title or ""))


def is_engineering(title: str, department: str = "") -> bool:
    """Engineering by title, unless the title also names a non-engineering role.

    The exclusion wins on purpose. "Via Student Transit" is a product name
    attached to Field Operations Manager postings in this corpus; without the
    exclusion those would read as student engineering jobs.
    """
    title = title or ""
    if NOT_ENGINEERING.search(title):
        return False
    if ENGINEERING.search(title):
        return True
    # Department alone is too noisy to promote a title, but an unambiguous
    # engineering department plus a title with no role word at all (e.g.
    # "Backend - Core") is worth keeping.
    return bool(re.search(r"(?<!\w)(r&d|engineering|development)(?!\w)", department or "", re.I)) \
        and not NOT_ENGINEERING.search(department or "")
