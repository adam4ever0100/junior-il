"""Generate the published page.

One static HTML file plus the JSON behind it, written to `docs/` — the directory name GitHub Pages
    will serve from a branch, which is why it is not called `site`. No build
step, no framework, no server: a scheduled job regenerates the files and
commits them, which also means the data's history lives in git where anyone
can audit how a number changed.

Nothing here decides anything. Every figure arrives already computed from
`index.py`, so the page cannot disagree with `junior-il index`.
"""
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from html import escape
from pathlib import Path
from typing import Any, Optional

REPO = "https://github.com/adam4ever0100/junior-il"
CONTACT = "adamabusaad@gmail.com"

# Pinned exactly, from cdnjs. A floating version would let the page break
# without anything in this repository changing.
CHART_JS = "https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js"

BUCKET_ORDER = ("0-1", "2", "3-4", "5+", "unquantified", "unstated")


@dataclass(frozen=True)
class Language:
    """One rendered page.

    Two documents rather than one page with a JavaScript switch: Hebrew needs
    `lang="he" dir="rtl"` on the document itself, the page then works with no
    JavaScript at all, and a Hebrew URL can be sent to a Hebrew-reading
    recruiter directly instead of asking them to click a toggle.
    """
    code: str
    direction: str
    filename: str
    other_name: str     # link text pointing at the other language
    other_file: str
    buckets: dict[str, str]
    strings: dict[str, str]


ENGLISH = Language(
    code="en", direction="ltr", filename="index.html",
    other_name="\u05e2\u05d1\u05e8\u05d9\u05ea", other_file="he.html",
    buckets={
        "0-1": "0\u20131 years", "2": "2 years", "3-4": "3\u20134 years",
        "5+": "5+ years", "unquantified": "\u201cseveral years\u201d",
        "unstated": "not stated",
    },
    strings={
        "title": "Junior Hiring Index \u2014 Israel",
        "description": "How much of the Israeli tech market is open to a computer "
                       "science graduate with no professional experience. Measured "
                       "from companies' own public job boards, with the method published.",
        "h1": "How open is Israeli tech to a graduate with no experience?",
        "lede": "Measured from {boards} companies' own public job boards, not from "
                "opinion. Updated automatically; the method is published.",
        # A noun phrase, not a sentence with a verb: the hero number is 0 one
        # week and 4 the next, and "1 ... state an experience requirement" is
        # wrong English. The relative clause agrees with "roles" instead, so
        # the wording survives any value.
        "hero_caption": "\u2014 the number of Israel-based engineering roles, out of "
                        "<strong>{il_eng}</strong> open, that state an experience "
                        "requirement a graduate could meet.",
        "sub_none": "No open engineering role in the sample can be applied to by a "
                    "graduate at all.",
        "sub_no_invite": "{eligible} can be applied to in total \u2014 but only because "
                         "they state no experience requirement at all, not because they "
                         "invite someone starting out. The door is not ajar; it is "
                         "unlabelled.",
        "sub_all_invite": "{eligible} can be applied to in total, and each one says so "
                          "explicitly.",
        "sub_mixed": "{eligible} can be applied to in total: {invited} that invites a "
                     "graduate outright, and {silent} that simply state no requirement "
                     "at all. Most of the open door is an omission rather than an "
                     "invitation.",
        "stat_israel": "open roles located in Israel",
        "stat_eng": "of those, engineering",
        "stat_3plus": "demand 3+ years",
        "stat_degree": "require a degree",
        "stat_junior_titled": "junior-titled, any field",
        "h_bar": "The experience bar",
        "p_bar": "Every stated requirement, read as the steepest figure a candidate "
                 "must clear. A range states its floor: \u201c4\u20138 years\u201d counts as "
                 "four. Postings that never mention experience are kept separate from "
                 "postings that ask for none.",
        "h_apply": "Where a graduate can apply",
        "none_apply": "Not one open engineering role in the sample is open to a "
                      "graduate with no professional experience.",
        "h_company": "By company",
        "th_company": "Company", "th_eng": "IL eng.", "th_3": "3+ yrs",
        "th_5": "5+ yrs", "th_grad": "Open to a grad",
        "h_time": "Over time",
        "first_snapshot": "This is the first snapshot. A single measurement is not a "
                          "trend, so there is nothing to plot yet \u2014 come back next month.",
        "method": "<strong>Method.</strong> What counts as Israel, as engineering, and "
                  "as an experience requirement is written down in "
                  "<a href=\"{repo}/blob/main/METHOD.md\">METHOD.md</a>, together with the "
                  "limits of the sample: {boards} company boards on Greenhouse and Comeet "
                  "only, so Workday employers, agencies and roles posted on LinkedIn alone "
                  "are absent. Corrections are worth more to me than agreement \u2014 "
                  "<a href=\"{repo}/issues\">open an issue</a>.",
        "sweep": "Sweep <strong>{status}</strong> ({ok}/{total} boards answered, "
                 "{retired} retired) \u00b7 parser <code>{parser}</code> \u00b7 generated "
                 "{generated} UTC \u00b7 <a href=\"data/latest.json\">latest.json</a> \u00b7 "
                 "<a href=\"{repo}\">source</a>",
        "status_complete": "complete", "status_partial": "partial",
        "bio": "Built by Adam Abu Saad \u2014 B.Sc. Computer Science, Shamoon College of "
               "Engineering, graduating June 2026. I started measuring this market "
               "because I am in it, and the data I wanted did not exist.",
        "roles_tooltip": "roles",
    },
)

HEBREW = Language(
    code="he", direction="rtl", filename="he.html",
    other_name="English", other_file="index.html",
    buckets={
        "0-1": "0\u20131 \u05e9\u05e0\u05d9\u05dd", "2": "\u05e9\u05e0\u05ea\u05d9\u05d9\u05dd",
        "3-4": "3\u20134 \u05e9\u05e0\u05d9\u05dd", "5+": "5+ \u05e9\u05e0\u05d9\u05dd",
        "unquantified": "\u201c\u05db\u05de\u05d4 \u05e9\u05e0\u05d9\u05dd\u201d",
        "unstated": "\u05dc\u05d0 \u05e6\u05d5\u05d9\u05df",
    },
    # Hebrew conjugates with the number, and these numbers change on every
    # run. Each sentence here is phrased to be agreement-free — a count is
    # followed by a noun phrase, never by a verb that would have to agree
    # with it — so the page cannot become ungrammatical when the data moves.
    strings={
        "title": "\u05de\u05d3\u05d3 \u05d2\u05d9\u05d5\u05e1 \u05d4\u05d2'\u05d5\u05e0\u05d9\u05d5\u05e8\u05d9\u05dd \u2014 \u05d9\u05e9\u05e8\u05d0\u05dc",
        "description": "\u05e2\u05d3 \u05db\u05de\u05d4 \u05e9\u05d5\u05e7 \u05d4\u05d4\u05d9\u05d9\u05d8\u05e7 \u05d4\u05d9\u05e9\u05e8\u05d0\u05dc\u05d9 \u05e4\u05ea\u05d5\u05d7 \u05dc\u05d1\u05d5\u05d2\u05e8 \u05de\u05d3\u05e2\u05d9 \u05d4\u05de\u05d7\u05e9\u05d1 \u05dc\u05dc\u05d0 \u05e0\u05d9\u05e1\u05d9\u05d5\u05df \u05de\u05e7\u05e6\u05d5\u05e2\u05d9. \u05e0\u05de\u05d3\u05d3 \u05de\u05dc\u05d5\u05d7\u05d5\u05ea \u05d4\u05de\u05e9\u05e8\u05d5\u05ea \u05d4\u05e4\u05d5\u05de\u05d1\u05d9\u05d9\u05dd \u05e9\u05dc \u05d4\u05d7\u05d1\u05e8\u05d5\u05ea \u05e2\u05e6\u05de\u05df.",
        "h1": "\u05e2\u05d3 \u05db\u05de\u05d4 \u05d4\u05d4\u05d9\u05d9\u05d8\u05e7 \u05d4\u05d9\u05e9\u05e8\u05d0\u05dc\u05d9 \u05e4\u05ea\u05d5\u05d7 \u05dc\u05d1\u05d5\u05d2\u05e8 \u05dc\u05dc\u05d0 \u05e0\u05d9\u05e1\u05d9\u05d5\u05df?",
        "lede": "\u05e0\u05de\u05d3\u05d3 \u05de\u05dc\u05d5\u05d7\u05d5\u05ea \u05d4\u05de\u05e9\u05e8\u05d5\u05ea \u05d4\u05e4\u05d5\u05de\u05d1\u05d9\u05d9\u05dd \u05e9\u05dc {boards} \u05d7\u05d1\u05e8\u05d5\u05ea, \u05dc\u05d0 \u05de\u05d3\u05e2\u05d5\u05ea. \u05de\u05ea\u05e2\u05d3\u05db\u05df \u05d0\u05d5\u05d8\u05d5\u05de\u05d8\u05d9\u05ea; \u05d4\u05de\u05ea\u05d5\u05d3\u05d5\u05dc\u05d5\u05d2\u05d9\u05d4 \u05de\u05e4\u05d5\u05e8\u05e1\u05de\u05ea.",
        "hero_caption": "\u2014 מספר משרות ההנדסה בישראל, מתוך "
                        "<strong>{il_eng}</strong> פתוחות, שמציינות דרישת ניסיון "
                        "שבוגר יכול לעמוד בה.",
        "sub_none": "\u05d0\u05e3 \u05de\u05e9\u05e8\u05ea \u05d4\u05e0\u05d3\u05e1\u05d4 \u05e4\u05ea\u05d5\u05d7\u05d4 \u05d1\u05de\u05d3\u05d2\u05dd \u05d0\u05d9\u05e0\u05d4 \u05e4\u05ea\u05d5\u05d7\u05d4 \u05dc\u05d1\u05d5\u05d2\u05e8 \u05dc\u05dc\u05d0 \u05e0\u05d9\u05e1\u05d9\u05d5\u05df \u05db\u05dc\u05dc.",
        "sub_no_invite": "\u05dc-{eligible} \u05d0\u05e4\u05e9\u05e8 \u05dc\u05d4\u05d2\u05d9\u05e9 \u05d1\u05e1\u05da \u05d4\u05db\u05d5\u05dc \u2014 \u05d0\u05da \u05e8\u05e7 \u05de\u05e9\u05d5\u05dd \u05e9\u05d0\u05d9\u05e0\u05df \u05de\u05e6\u05d9\u05d9\u05e0\u05d5\u05ea \u05d3\u05e8\u05d9\u05e9\u05ea \u05e0\u05d9\u05e1\u05d9\u05d5\u05df \u05db\u05dc\u05dc, \u05dc\u05d0 \u05de\u05e9\u05d5\u05dd \u05e9\u05d4\u05df \u05de\u05d6\u05de\u05d9\u05e0\u05d5\u05ea \u05de\u05d9 \u05e9\u05e8\u05e7 \u05de\u05ea\u05d7\u05d9\u05dc. \u05d4\u05d3\u05dc\u05ea \u05d0\u05d9\u05e0\u05d4 \u05e4\u05ea\u05d5\u05d7\u05d4 \u2014 \u05d4\u05d9\u05d0 \u05e4\u05e9\u05d5\u05d8 \u05dc\u05d0 \u05de\u05e1\u05d5\u05de\u05e0\u05ea.",
        "sub_all_invite": "\u05dc-{eligible} \u05d0\u05e4\u05e9\u05e8 \u05dc\u05d4\u05d2\u05d9\u05e9 \u05d1\u05e1\u05da \u05d4\u05db\u05d5\u05dc, \u05d5\u05db\u05dc \u05d0\u05d7\u05ea \u05de\u05d4\u05df \u05d0\u05d5\u05de\u05e8\u05ea \u05d6\u05d0\u05ea \u05d1\u05de\u05e4\u05d5\u05e8\u05e9.",
        "sub_mixed": "\u05dc-{eligible} \u05d0\u05e4\u05e9\u05e8 \u05dc\u05d4\u05d2\u05d9\u05e9 \u05d1\u05e1\u05da \u05d4\u05db\u05d5\u05dc: {invited} \u05d1\u05d6\u05db\u05d5\u05ea \u05d4\u05d6\u05de\u05e0\u05d4 \u05de\u05e4\u05d5\u05e8\u05e9\u05ea, \u05d5-{silent} \u05e8\u05e7 \u05de\u05e9\u05d5\u05dd \u05d4\u05d9\u05e2\u05d3\u05e8 \u05d3\u05e8\u05d9\u05e9\u05d4 \u05db\u05dc\u05e9\u05d4\u05d9. \u05e8\u05d5\u05d1 \u05d4\u05d3\u05dc\u05ea \u05d4\u05e4\u05ea\u05d5\u05d7\u05d4 \u05d4\u05d9\u05d0 \u05d4\u05e9\u05de\u05d8\u05d4 \u05d5\u05dc\u05d0 \u05d4\u05d6\u05de\u05e0\u05d4.",
        "stat_israel": "\u05de\u05e9\u05e8\u05d5\u05ea \u05e4\u05ea\u05d5\u05d7\u05d5\u05ea \u05d1\u05d9\u05e9\u05e8\u05d0\u05dc",
        "stat_eng": "\u05de\u05ea\u05d5\u05db\u05df, \u05d4\u05e0\u05d3\u05e1\u05d4",
        "stat_3plus": "\u05d3\u05d5\u05e8\u05e9\u05d5\u05ea 3+ \u05e9\u05e0\u05d9\u05dd",
        "stat_degree": "\u05d3\u05d5\u05e8\u05e9\u05d5\u05ea \u05ea\u05d5\u05d0\u05e8",
        "stat_junior_titled": "\u05e2\u05dd \u05ea\u05d5\u05d0\u05e8 \u05d2'\u05d5\u05e0\u05d9\u05d5\u05e8, \u05d1\u05db\u05dc \u05ea\u05d7\u05d5\u05dd",
        "h_bar": "\u05e8\u05e3 \u05d4\u05e0\u05d9\u05e1\u05d9\u05d5\u05df",
        "p_bar": "\u05db\u05dc \u05d3\u05e8\u05d9\u05e9\u05d4 \u05e9\u05e6\u05d5\u05d9\u05e0\u05d4, \u05e0\u05e7\u05e8\u05d0\u05ea \u05db\u05e8\u05e3 \u05d4\u05d2\u05d1\u05d5\u05d4 \u05d1\u05d9\u05d5\u05ea\u05e8 \u05e9\u05e2\u05dc \u05de\u05d5\u05e2\u05de\u05d3 \u05dc\u05e2\u05de\u05d5\u05d3 \u05d1\u05d5. \u05d8\u05d5\u05d5\u05d7 \u05de\u05e6\u05d9\u05d9\u05df \u05d0\u05ea \u05e8\u05e6\u05e4\u05ea\u05d5: \u201c4\u20138 \u05e9\u05e0\u05d9\u05dd\u201d \u05e0\u05e1\u05e4\u05e8 \u05db\u05d0\u05e8\u05d1\u05e2. \u05de\u05e9\u05e8\u05d5\u05ea \u05e9\u05d0\u05d9\u05e0\u05df \u05de\u05d6\u05db\u05d9\u05e8\u05d5\u05ea \u05e0\u05d9\u05e1\u05d9\u05d5\u05df \u05e0\u05e9\u05de\u05e8\u05d5\u05ea \u05d1\u05e0\u05e4\u05e8\u05d3 \u05de\u05de\u05e9\u05e8\u05d5\u05ea \u05e9\u05d0\u05d9\u05e0\u05df \u05d3\u05d5\u05e8\u05e9\u05d5\u05ea \u05d0\u05d5\u05ea\u05d5.",
        "h_apply": "\u05d4\u05d9\u05db\u05df \u05d1\u05d5\u05d2\u05e8 \u05d9\u05db\u05d5\u05dc \u05dc\u05d4\u05d2\u05d9\u05e9",
        "none_apply": "\u05d0\u05e3 \u05de\u05e9\u05e8\u05ea \u05d4\u05e0\u05d3\u05e1\u05d4 \u05e4\u05ea\u05d5\u05d7\u05d4 \u05d1\u05de\u05d3\u05d2\u05dd \u05d0\u05d9\u05e0\u05d4 \u05e4\u05ea\u05d5\u05d7\u05d4 \u05dc\u05d1\u05d5\u05d2\u05e8 \u05dc\u05dc\u05d0 \u05e0\u05d9\u05e1\u05d9\u05d5\u05df \u05de\u05e7\u05e6\u05d5\u05e2\u05d9.",
        "h_company": "\u05dc\u05e4\u05d9 \u05d7\u05d1\u05e8\u05d4",
        "th_company": "\u05d7\u05d1\u05e8\u05d4", "th_eng": "\u05d4\u05e0\u05d3\u05e1\u05d4 \u05d1\u05d9\u05e9\u05e8\u05d0\u05dc",
        "th_3": "3+ \u05e9\u05e0\u05d9\u05dd", "th_5": "5+ \u05e9\u05e0\u05d9\u05dd",
        "th_grad": "\u05e4\u05ea\u05d5\u05d7 \u05dc\u05d1\u05d5\u05d2\u05e8",
        "h_time": "\u05dc\u05d0\u05d5\u05e8\u05da \u05d6\u05de\u05df",
        "first_snapshot": "\u05d6\u05d5 \u05d4\u05de\u05d3\u05d9\u05d3\u05d4 \u05d4\u05e8\u05d0\u05e9\u05d5\u05e0\u05d4. \u05de\u05d3\u05d9\u05d3\u05d4 \u05d0\u05d7\u05ea \u05d0\u05d9\u05e0\u05d4 \u05de\u05d2\u05de\u05d4, \u05d5\u05dc\u05db\u05df \u05d0\u05d9\u05df \u05e2\u05d3\u05d9\u05d9\u05df \u05de\u05d4 \u05dc\u05e9\u05e8\u05d8\u05d8 \u2014 \u05d7\u05d6\u05e8\u05d5 \u05d1\u05d7\u05d5\u05d3\u05e9 \u05d4\u05d1\u05d0.",
        "method": "<strong>\u05de\u05ea\u05d5\u05d3\u05d5\u05dc\u05d5\u05d2\u05d9\u05d4.</strong> \u05de\u05d4 \u05e0\u05d7\u05e9\u05d1 \u05d9\u05e9\u05e8\u05d0\u05dc, \u05de\u05d4 \u05e0\u05d7\u05e9\u05d1 \u05d4\u05e0\u05d3\u05e1\u05d4 \u05d5\u05de\u05d4\u05d9 \u05d3\u05e8\u05d9\u05e9\u05ea \u05e0\u05d9\u05e1\u05d9\u05d5\u05df \u2014 \u05d4\u05db\u05d5\u05dc \u05db\u05ea\u05d5\u05d1 \u05d1-<a href=\"{repo}/blob/main/METHOD.md\">METHOD.md</a>, \u05d9\u05d7\u05d3 \u05e2\u05dd \u05de\u05d2\u05d1\u05dc\u05d5\u05ea \u05d4\u05de\u05d3\u05d2\u05dd: {boards} \u05dc\u05d5\u05d7\u05d5\u05ea \u05de\u05e9\u05e8\u05d5\u05ea \u05d1-Greenhouse \u05d5\u05d1-Comeet \u05d1\u05dc\u05d1\u05d3, \u05db\u05da \u05e9\u05de\u05e2\u05e1\u05d9\u05e7\u05d9\u05dd \u05d1-Workday, \u05d7\u05d1\u05e8\u05d5\u05ea \u05d4\u05e9\u05de\u05d4 \u05d5\u05de\u05e9\u05e8\u05d5\u05ea \u05e9\u05de\u05ea\u05e4\u05e8\u05e1\u05de\u05d5\u05ea \u05e8\u05e7 \u05d1\u05dc\u05d9\u05e0\u05e7\u05d3\u05d0\u05d9\u05df \u05d0\u05d9\u05e0\u05df \u05e0\u05db\u05dc\u05dc\u05d5\u05ea. \u05ea\u05d9\u05e7\u05d5\u05e0\u05d9\u05dd \u05e9\u05d5\u05d5\u05d9\u05dd \u05dc\u05d9 \u05d9\u05d5\u05ea\u05e8 \u05de\u05d4\u05e1\u05db\u05de\u05d4 \u2014 <a href=\"{repo}/issues\">\u05e4\u05ea\u05d7\u05d5 issue</a>.",
        "sweep": "\u05e1\u05e8\u05d9\u05e7\u05d4 <strong>{status}</strong> ({ok}/{total} \u05dc\u05d5\u05d7\u05d5\u05ea \u05d4\u05d2\u05d9\u05d1\u05d5, {retired} \u05d4\u05d5\u05e6\u05d0\u05d5 \u05de\u05e9\u05d9\u05de\u05d5\u05e9) \u00b7 \u05de\u05e0\u05ea\u05d7 <code>{parser}</code> \u00b7 \u05e0\u05d5\u05e6\u05e8 {generated} UTC \u00b7 <a href=\"data/latest.json\">latest.json</a> \u00b7 <a href=\"{repo}\">\u05e7\u05d5\u05d3 \u05d4\u05de\u05e7\u05d5\u05e8</a>",
        "status_complete": "\u05de\u05dc\u05d0\u05d4", "status_partial": "\u05d7\u05dc\u05e7\u05d9\u05ea",
        "bio": "\u05e0\u05d1\u05e0\u05d4 \u05e2\u05dc \u05d9\u05d3\u05d9 \u05d0\u05d3\u05dd \u05d0\u05d1\u05d5 \u05e1\u05e2\u05d3 \u2014 \u05ea\u05d5\u05d0\u05e8 \u05e8\u05d0\u05e9\u05d5\u05df \u05d1\u05de\u05d3\u05e2\u05d9 \u05d4\u05de\u05d7\u05e9\u05d1, \u05d4\u05de\u05db\u05dc\u05dc\u05d4 \u05d4\u05d0\u05e7\u05d3\u05de\u05d9\u05ea \u05dc\u05d4\u05e0\u05d3\u05e1\u05d4 \u05e2\u05f4\u05e9 \u05e1\u05de\u05d9 \u05e9\u05de\u05e2\u05d5\u05df, \u05e1\u05d9\u05d5\u05dd \u05d9\u05d5\u05e0\u05d9 2026. \u05d4\u05ea\u05d7\u05dc\u05ea\u05d9 \u05dc\u05de\u05d3\u05d5\u05d3 \u05d0\u05ea \u05d4\u05e9\u05d5\u05e7 \u05d4\u05d6\u05d4 \u05db\u05d9 \u05d0\u05e0\u05d9 \u05d1\u05ea\u05d5\u05db\u05d5, \u05d5\u05d4\u05e0\u05ea\u05d5\u05e0\u05d9\u05dd \u05e9\u05e8\u05e6\u05d9\u05ea\u05d9 \u05dc\u05d0 \u05d4\u05d9\u05d5 \u05e7\u05d9\u05d9\u05de\u05d9\u05dd.",
        "roles_tooltip": "\u05de\u05e9\u05e8\u05d5\u05ea",
    },
)

LANGUAGES = (ENGLISH, HEBREW)


def _json_for_script(payload: Any) -> str:
    """JSON safe to inline in a <script> tag."""
    return json.dumps(payload, default=str).replace("</", "<\\/")


def _day(taken_at: Any) -> str:
    """A date, whether it came from Postgres or from a JSON round-trip.

    The series is reloaded from published JSON in CI, where timestamps arrive
    as strings rather than datetimes.
    """
    if isinstance(taken_at, str):
        return taken_at[:10]
    return taken_at.strftime("%Y-%m-%d")


def _stat(value: Any, label: str) -> str:
    return (f'<div class="stat"><div class="stat-n">{escape(str(value))}</div>'
            f'<div class="stat-l">{label}</div></div>')


def _company_rows(companies: list[dict]) -> str:
    rows = []
    for row in companies:
        rows.append(
            "<tr>"
            f'<td>{escape(row["company"])}</td>'
            f'<td class="n">{row["il_eng"]}</td>'
            f'<td class="n">{row["bar_3plus"]}</td>'
            f'<td class="n">{row["bar_5plus"]}</td>'
            f'<td class="n{" zero" if not row["eligible"] else ""}">{row["eligible"]}</td>'
            "</tr>"
        )
    return "\n".join(rows)


def _eligible_list(roles: list[dict], lang: Language) -> str:
    if not roles:
        return f'<p class="none">{lang.strings["none_apply"]}</p>'
    items = []
    for role in roles:
        label = f'{escape(role["title"])} \u2014 {escape(role["company"])}'
        location = escape(role["location_raw"] or "")
        url = role["url"] or ""
        link = (f'<a href="{escape(url, quote=True)}" rel="nofollow noopener" '
                f'target="_blank">{label}</a>') if url else label
        # Role titles and locations stay in the language the employer wrote
        # them in; dir="auto" lets each line lay itself out correctly inside
        # an RTL page rather than forcing Latin text to read right-to-left.
        items.append(f'<li dir="auto">{link} <span class="loc">{location}</span></li>')
    return f'<ul class="roles">{"".join(items)}</ul>'


def _hero_sub(lang: Language, eligible: int, invited: int) -> str:
    """The claim about *why* those roles are open, derived from the numbers.

    Hardcoding it once produced a sentence that was true in the morning and
    false by the evening, so each case is a separate template and the right
    one is chosen from the data.
    """
    silent = eligible - invited
    if eligible == 0:
        key = "sub_none"
    elif invited == 0:
        key = "sub_no_invite"
    elif silent == 0:
        key = "sub_all_invite"
    else:
        key = "sub_mixed"
    return lang.strings[key].format(eligible=eligible, invited=invited, silent=silent)


def render_html(
    counts: dict,
    histogram: list[dict],
    companies: list[dict],
    eligible: list[dict],
    series: list[dict],
    generated_at: datetime,
    lang: Language = ENGLISH,
) -> str:
    text = lang.strings
    buckets = {row["bucket"]: row["roles"] for row in histogram}
    # Every bucket is drawn, including the empty ones. A GROUP BY omits a
    # bucket with no rows, which silently deleted the "0-1 years" bar — the
    # one fact the whole page is about. An absence has to be visible as a
    # flat zero, not as a missing column nobody notices.
    chart_data = {
        "labels": [lang.buckets[b] for b in BUCKET_ORDER],
        "values": [buckets.get(b, 0) for b in BUCKET_ORDER],
        "rtl": lang.direction == "rtl",
        "roles": text["roles_tooltip"],
    }
    # Oldest first, so the line reads left to right.
    trend = [
        {"date": _day(row["taken_at"]),
         "pct": float(row["pct_junior_eligible"] or 0),
         "eligible": row["junior_eligible"],
         "total": row["open_israel_eng"]}
        for row in reversed(series)
    ]

    il_eng = counts["open_israel_eng"]
    invited = counts["explicit_entry"]
    eligible_n = counts["junior_eligible"]
    status = text["status_complete"] if counts["status"] == "complete" \
        else text["status_partial"]
    other_code = "he" if lang.code == "en" else "en"

    trend_block = (
        '<figure><div class="chart"><canvas id="trend"></canvas></div></figure>'
        if len(trend) > 1 else f'<p>{text["first_snapshot"]}</p>'
    )

    return f"""<!doctype html>
<html lang="{lang.code}" dir="{lang.direction}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{text["title"]}</title>
<meta name="description" content="{escape(text["description"], quote=True)}">
<link rel="alternate" hreflang="{LANGUAGES[0].code}" href="{LANGUAGES[0].filename}">
<link rel="alternate" hreflang="{LANGUAGES[1].code}" href="{LANGUAGES[1].filename}">
<script src="{CHART_JS}" defer></script>
<style>
:root {{
  --bg:#fbfaf8; --fg:#1b1a18; --muted:#6b6862; --rule:#e3dfd8;
  --accent:#b4332b; --card:#fff;
}}
@media (prefers-color-scheme: dark) {{
  :root {{ --bg:#17161a; --fg:#ece9e4; --muted:#a39e96; --rule:#322f36;
           --accent:#ff7a6b; --card:#1f1e23; }}
}}
* {{ box-sizing:border-box; }}
body {{
  margin:0; background:var(--bg); color:var(--fg);
  font:16px/1.6 -apple-system,BlinkMacSystemFont,"Segoe UI",Helvetica,Arial,sans-serif;
  -webkit-text-size-adjust:100%;
}}
.wrap {{ max-width:860px; margin:0 auto; padding:48px 16px 72px; }}
h1 {{ font-size:1.55rem; line-height:1.25; margin:0 0 .4em; letter-spacing:-.01em; }}
h2 {{ font-size:1.05rem; margin:2.6em 0 .7em; letter-spacing:.02em;
      text-transform:uppercase; color:var(--muted); font-weight:600; }}
p {{ margin:0 0 1em; max-width:62ch; }}
a {{ color:var(--accent); }}
.lede {{ color:var(--muted); }}
.langs {{ float:inline-end; font-size:.9rem; }}
.hero {{ border:1px solid var(--rule); background:var(--card); border-radius:10px;
        padding:28px 24px; margin:28px 0; }}
.hero-n {{ font-size:clamp(3.6rem,17vw,6rem); line-height:.9; font-weight:700;
          letter-spacing:-.04em; color:var(--accent); }}
.hero-c {{ font-size:1.08rem; margin:.5em 0 0; max-width:48ch; }}
.hero-sub {{ margin:1.1em 0 0; padding-top:1.1em; border-top:1px solid var(--rule);
            color:var(--muted); font-size:.95rem; max-width:52ch; }}
.stats {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(130px,1fr));
         gap:1px; background:var(--rule); border:1px solid var(--rule);
         border-radius:10px; overflow:hidden; }}
.stat {{ background:var(--card); padding:16px 18px; }}
.stat-n {{ font-size:1.65rem; font-weight:650; letter-spacing:-.02em; }}
.stat-l {{ color:var(--muted); font-size:.82rem; line-height:1.4; }}
figure {{ margin:0; }}
.chart {{ position:relative; height:300px; }}
table {{ width:100%; border-collapse:collapse; font-size:.92rem; }}
.scroll {{ overflow-x:auto; -webkit-overflow-scrolling:touch; }}
/* Logical properties, so the table flips with the document instead of
   needing a second set of rules for Hebrew. */
th,td {{ text-align:start; padding:9px 12px; border-bottom:1px solid var(--rule);
        white-space:nowrap; }}
th {{ color:var(--muted); font-weight:600; font-size:.78rem;
      text-transform:uppercase; letter-spacing:.04em; }}
td.n, th.n {{ text-align:end; font-variant-numeric:tabular-nums; }}
td.zero {{ color:var(--muted); }}
.roles {{ list-style:none; padding:0; margin:0; }}
.roles li {{ padding:11px 0; border-bottom:1px solid var(--rule); }}
.loc {{ color:var(--muted); font-size:.85rem; display:block; }}
.none {{ font-size:1.05rem; }}
footer {{ margin-top:56px; padding-top:24px; border-top:1px solid var(--rule);
         color:var(--muted); font-size:.85rem; }}
footer p {{ max-width:70ch; }}
code {{ font-size:.85em; }}
</style>
</head>
<body>
<div class="wrap">

<p class="langs"><a href="{lang.other_file}" lang="{other_code}"
   hreflang="{other_code}">{lang.other_name}</a></p>

<h1>{text["h1"]}</h1>
<p class="lede">{text["lede"].format(boards=counts["boards_total"])}</p>

<div class="hero">
  <div class="hero-n">{invited}</div>
  <p class="hero-c">{text["hero_caption"].format(il_eng=il_eng)}</p>
  <p class="hero-sub">{_hero_sub(lang, eligible_n, invited)}</p>
</div>

<div class="stats">
  {_stat(counts['open_israel'], text["stat_israel"])}
  {_stat(il_eng, text["stat_eng"])}
  {_stat(counts['bar_3plus'], text["stat_3plus"])}
  {_stat(counts['degree_required'], text["stat_degree"])}
  {_stat(counts['junior_titled'], text["stat_junior_titled"])}
</div>

<h2>{text["h_bar"]}</h2>
<p>{text["p_bar"]}</p>
<figure><div class="chart"><canvas id="bars"></canvas></div></figure>

<h2>{text["h_apply"]}</h2>
{_eligible_list(eligible, lang)}

<h2>{text["h_company"]}</h2>
<div class="scroll"><table>
<thead><tr><th>{text["th_company"]}</th><th class="n">{text["th_eng"]}</th>
<th class="n">{text["th_3"]}</th><th class="n">{text["th_5"]}</th>
<th class="n">{text["th_grad"]}</th></tr></thead>
<tbody>
{_company_rows(companies)}
</tbody></table></div>

<h2>{text["h_time"]}</h2>
{trend_block}

<footer>
<p>{text["method"].format(repo=REPO, boards=counts["boards_total"])}</p>
<p>{text["sweep"].format(
    status=status, ok=counts["boards_ok"], total=counts["boards_total"],
    retired=counts["boards_retired"], parser=escape(counts["parser_version"]),
    generated=f"{generated_at:%Y-%m-%d %H:%M}", repo=REPO)}</p>
<p>{text["bio"]} <a href="mailto:{CONTACT}">{CONTACT}</a></p>
</footer>
</div>

<script id="payload" type="application/json">{_json_for_script(
    {"bars": chart_data, "trend": trend})}</script>
<script>
window.addEventListener('load', function () {{
  if (typeof Chart === 'undefined') return;
  var data = JSON.parse(document.getElementById('payload').textContent);
  var css = getComputedStyle(document.documentElement);
  var accent = css.getPropertyValue('--accent').trim();
  var muted = css.getPropertyValue('--muted').trim();
  var rule = css.getPropertyValue('--rule').trim();
  Chart.defaults.color = muted;
  Chart.defaults.font.family = getComputedStyle(document.body).fontFamily;
  // In an RTL document the value axis belongs on the right, and the
  // categories read right to left.
  var axis = data.bars.rtl ? 'right' : 'left';

  new Chart(document.getElementById('bars'), {{
    type: 'bar',
    data: {{ labels: data.bars.labels,
             datasets: [{{ data: data.bars.values, backgroundColor: accent,
                          borderRadius: 3 }}] }},
    options: {{ responsive: true, maintainAspectRatio: false,
      plugins: {{ legend: {{ display: false }},
        tooltip: {{ rtl: data.bars.rtl, callbacks: {{ label: function (c) {{
          return c.parsed.y + ' ' + data.bars.roles; }} }} }} }},
      scales: {{ x: {{ reverse: data.bars.rtl, grid: {{ display: false }} }},
                 y: {{ position: axis, beginAtZero: true, grid: {{ color: rule }},
                       ticks: {{ precision: 0 }} }} }} }}
  }});

  var trendCanvas = document.getElementById('trend');
  if (trendCanvas && data.trend.length > 1) {{
    new Chart(trendCanvas, {{
      type: 'line',
      data: {{ labels: data.trend.map(function (p) {{ return p.date; }}),
               datasets: [{{ data: data.trend.map(function (p) {{ return p.pct; }}),
                            borderColor: accent, backgroundColor: accent,
                            tension: .2, pointRadius: 3 }}] }},
      options: {{ responsive: true, maintainAspectRatio: false,
        plugins: {{ legend: {{ display: false }},
          tooltip: {{ rtl: data.bars.rtl, callbacks: {{ label: function (c) {{
            var p = data.trend[c.dataIndex];
            return p.eligible + ' / ' + p.total + ' (' + p.pct + '%)'; }} }} }} }},
        scales: {{ x: {{ grid: {{ display: false }} }},
                   y: {{ position: axis, beginAtZero: true, grid: {{ color: rule }},
                         ticks: {{ callback: function (v) {{ return v + '%'; }} }} }} }} }}
    }});
  }}
}});
</script>
</body>
</html>
"""


def build(
    out_dir: Path,
    counts: dict,
    histogram: list[dict],
    companies: list[dict],
    eligible: list[dict],
    series: list[dict],
    generated_at: Optional[datetime] = None,
) -> list[Path]:
    generated_at = generated_at or datetime.now(timezone.utc)
    out_dir = Path(out_dir)
    (out_dir / "data").mkdir(parents=True, exist_ok=True)

    latest = {
        "generated_at": generated_at.isoformat(),
        "index": counts,
        "experience_bar": {row["bucket"]: row["roles"] for row in histogram},
        "companies": [dict(row) for row in companies],
        "junior_eligible_roles": [dict(row) for row in eligible],
        "method": f"{REPO}/blob/main/METHOD.md",
    }
    written = []
    for name, payload in (
        ("data/latest.json", latest),
        ("data/series.json", [dict(row) for row in series]),
    ):
        path = out_dir / name
        path.write_text(json.dumps(payload, indent=2, default=str) + "\n",
                        encoding="utf-8")
        written.append(path)

    # Both languages from the same numbers, in one pass, so they cannot drift.
    for lang in LANGUAGES:
        page = out_dir / lang.filename
        page.write_text(
            render_html(counts, histogram, companies, eligible, series,
                        generated_at, lang=lang),
            encoding="utf-8",
        )
        written.append(page)
    return written
