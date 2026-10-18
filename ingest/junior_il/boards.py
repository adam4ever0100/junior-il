"""Boards we poll.

Every token here was verified to return HTTP 200 from the Greenhouse API.
Israeli companies (HQ or a major R&D centre in Israel) — the point of the
dataset is the Israeli market, so a board with no Israeli roles is dead weight.

Keep this list in the repo rather than the database: it is a reviewed decision
about who counts as an Israeli employer, and it belongs in code review.
"""

GREENHOUSE_BOARDS: list[str] = [
    "appsflyer",
    "atbay",
    "augury",
    "bringg",
    "catonetworks",
    "fireblocks",
    "island",
    "jfrog",
    "lightricks",
    "melio",
    "nice",
    "optimove",
    "orcasecurity",
    "pagaya",
    "riskified",
    "similarweb",
    "taboola",
    "via",
    "yotpo",
]

# Retired, kept as a record of the decision rather than deleted silently:
#   "cybereason" — its Greenhouse board returned 404 from 18 Oct 2026. Its
#   postings were closed by `retire-boards` with closed_reason='board_retired'.

# Comeet needs two identifiers per board, so the slug maps to (uid, token).
# Both are public — they are lifted from the company's own careers page, whose
# JavaScript calls the same API — and both are verified against the live API by
# tools/find_comeet.py before being added here.
COMEET_BOARDS: dict[str, tuple[str, str]] = {
    "cycode": ("A8.00D", "8AD340E3CBB3CBB22B445680340E22B44568"),
    "gloat": ("E5.000", "5E02340002F0017800234011A01780"),
    "pentera": ("C5.00D", "5CD1D013435289B343501D012E682E68289B"),
    "zesty": ("06.000", "600240001E00030003000300024001E00"),
    "tastewise": ("F8.000", "8F035A047802CB047803E90478035A001AD0"),
}

ALL_BOARDS: list[tuple[str, str]] = (
    [("greenhouse", token) for token in GREENHOUSE_BOARDS]
    + [("comeet", slug) for slug in COMEET_BOARDS]
)
