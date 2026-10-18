"""Is this posting a job in Israel?

The hard part is not the word "Israel" — it is that most Israeli postings never
use it. In the September corpus, "Tel Aviv" alone was the single most common
location string, and a naive `location_raw ILIKE '%israel%'` found 119 of the
206 Israeli roles actually present. The missing 42% is why this module exists.
"""
import re

# Canonical name -> the spellings seen in the wild (and likely neighbours).
# Aliases are written lowercase, without apostrophes and with spaces for
# hyphens, because `_flatten` normalizes the input the same way before matching.
IL_CITIES: dict[str, tuple[str, ...]] = {
    "Tel Aviv":      ("tel aviv", "tel aviv yafo", "telaviv", "tlv", "תל אביב"),
    "Herzliya":      ("herzliya", "hertzliya", "herzelia", "herzliya pituach"),
    "Ra'anana":      ("raanana", "ranana"),
    "Netanya":       ("netanya", "natanya"),
    "Jerusalem":     ("jerusalem", "ירושלים"),
    "Haifa":         ("haifa", "חיפה"),
    "Glilot":        ("glilot",),
    "Givatayim":     ("givatayim", "givataim"),
    "Ramat Gan":     ("ramat gan",),
    "Petah Tikva":   ("petah tikva", "petach tikva", "petah tiqwa"),
    "Be'er Sheva":   ("beer sheva", "beersheba", "beer sheba", "באר שבע"),
    "Yokneam":       ("yokneam", "yoqneam"),
    "Caesarea":      ("caesarea",),
    "Rehovot":       ("rehovot",),
    "Hod Hasharon":  ("hod hasharon",),
    "Kfar Saba":     ("kfar saba", "kfar sava"),
    "Modi'in":       ("modiin",),
    "Airport City":  ("airport city",),
    "Rosh Ha'ayin":  ("rosh haayin", "rosh haain"),
    "Holon":         ("holon",),
    "Rishon LeZion": ("rishon lezion", "rishon letzion", "rishon le zion"),
    "Bnei Brak":     ("bnei brak",),
    "Nes Ziona":     ("nes ziona", "ness ziona"),
    "Or Yehuda":     ("or yehuda",),
    "Yavne":         ("yavne",),
    "Lod":           ("lod",),
    "Ashdod":        ("ashdod",),
    "Ashkelon":      ("ashkelon",),
    "Nazareth":      ("nazareth", "nof hagalil"),
    "Karmiel":       ("karmiel",),
    "Migdal Ha'emek": ("migdal haemek",),
    "Afula":         ("afula",),
    "Tirat Carmel":  ("tirat carmel",),
    "Omer":          ("omer",),
    "Hadera":        ("hadera",),
    "Zichron Ya'akov": ("zichron yaakov",),
    "Akko":          ("akko",),   # not "acre" — that is also a Brazilian state
    "Tiberias":      ("tiberias",),
    "Eilat":         ("eilat",),
    "Sderot":        ("sderot",),
    "Kiryat Gat":    ("kiryat gat",),
    "Kiryat Ono":    ("kiryat ono",),
    "Savyon":        ("savyon",),
}

COUNTRY_TOKENS = ("israel", "ישראל")

REMOTE_TOKENS = ("remote", "work from home", "wfh", "hybrid")

# Location fields pack several places into one string, in every style:
#   "Tel Aviv/ Netanya, Israel"   "Glilot; Tel Aviv"   "Israel - Raanana"
#   "New York City; San Francisco"
# Split on those separators, but never on a bare hyphen: that would cut
# "Tel Aviv-Yafo" and "Beer-Sheva" in half.
_SEPARATORS = re.compile(r"[;,/]|\s+[-–—]\s*|\s*[-–—]\s+")

_APOSTROPHES = str.maketrans({"'": "", "‘": "", "’": "", "`": "", "´": ""})


def _flatten(text: str) -> str:
    """Lowercase, drop apostrophes, turn hyphens into spaces, collapse runs.

    So "Giv'atayim", "Giv‘atayim" and "Givatayim" all become one string, and
    "Tel Aviv-Yafo" becomes "tel aviv yafo" where the alias "tel aviv" matches
    on a word boundary.
    """
    out = text.lower().translate(_APOSTROPHES)
    out = re.sub(r"[-–—]", " ", out)
    return re.sub(r"\s+", " ", out).strip()


def _alias_patterns() -> list[tuple[str, re.Pattern[str]]]:
    patterns = []
    for canonical, aliases in IL_CITIES.items():
        for alias in aliases:
            patterns.append((canonical, re.compile(rf"(?<!\w){re.escape(alias)}(?!\w)")))
    return patterns


_PATTERNS = _alias_patterns()


def segments(location_raw: str) -> list[str]:
    return [s for s in (p.strip() for p in _SEPARATORS.split(location_raw or "")) if s]


def classify(location_raw: str) -> tuple[bool, list[str], bool]:
    """Return (is_israel, canonical Israeli cities matched, is_remote).

    A posting counts as Israeli if *any* of its segments is in Israel, so a
    role listed "Tel Aviv; London" counts. That is the right answer for "can
    someone living here take this job", and it is stated in METHOD.md because
    it also means a global role listing six cities counts as one of them.
    """
    flat_segments = [_flatten(s) for s in segments(location_raw)]
    whole = _flatten(location_raw)

    cities: list[str] = []
    for canonical, pattern in _PATTERNS:
        if any(pattern.search(s) for s in flat_segments) and canonical not in cities:
            cities.append(canonical)

    in_israel = bool(cities) or any(
        re.search(rf"(?<!\w){token}(?!\w)", whole) for token in COUNTRY_TOKENS
    )
    is_remote = any(token in whole for token in REMOTE_TOKENS)
    return in_israel, sorted(cities), is_remote
