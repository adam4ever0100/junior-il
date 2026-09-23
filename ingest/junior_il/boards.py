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
    "cybereason",
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

ALL_BOARDS: list[tuple[str, str]] = [("greenhouse", t) for t in GREENHOUSE_BOARDS]
