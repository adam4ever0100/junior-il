"""Comeet career-site API.

Comeet is an Israeli ATS and widely used by Israeli companies, which is why it
is the second source: twenty Greenhouse boards is a product-company-weighted
sample, and that is the first thing anyone will say about the index.

A Comeet board needs two identifiers rather than one — a company uid like
"A8.00D" and a public token. Both are lifted from the company's own careers
page, whose JavaScript calls this same endpoint with them, so neither is a
secret. `tools/find_comeet.py` extracts and verifies a pair.

    https://www.comeet.co/careers-api/2.0/company/{uid}/positions?details=true
"""
from datetime import datetime
from typing import Any, Iterator, Optional

import httpx

from junior_il import config
from junior_il.boards import COMEET_BOARDS
from junior_il.htmltext import html_to_text
from junior_il.models import Posting
from junior_il.sources.base import fetch_json

API = "https://www.comeet.co/careers-api/2.0/company/{uid}/positions"


def _parse_ts(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _description(job: dict[str, Any]) -> str:
    """Join the posting's sections into one plain-text document.

    Comeet splits a posting into ordered sections ("Description",
    "Requirements", ...), each holding HTML. The section headings are kept and
    separated by blank lines, because the experience rules read one line at a
    time: a requirement glued to the end of the previous section is invisible
    to them.
    """
    sections = job.get("details") or []
    parts: list[str] = []
    for section in sorted(sections, key=lambda s: s.get("order") or 0):
        body = html_to_text(section.get("value") or "")
        if not body:
            continue
        name = (section.get("name") or "").strip()
        parts.append(f"{name}\n{body}" if name else body)
    return "\n\n".join(parts)


def _location(job: dict[str, Any]) -> str:
    location = job.get("location") or {}
    name = (location.get("name") or "").strip()
    if name:
        return name
    # Some boards leave `name` empty but still fill the parts. The structured
    # country code is deliberately *not* used to decide whether a role is in
    # Israel: the index applies one set of location rules to every source, so
    # that a number cannot shift because of which ATS a company happens to use.
    parts = [location.get("city"), location.get("state"), location.get("country")]
    return ", ".join(p for p in (x.strip() for x in parts if x) if p)


class ComeetSource:
    name = "comeet"

    def __init__(self, client: Optional[httpx.Client] = None) -> None:
        self._client = client or httpx.Client(
            timeout=config.REQUEST_TIMEOUT,
            headers={"User-Agent": config.USER_AGENT},
            follow_redirects=True,
        )

    def fetch(self, board_token: str) -> Iterator[Posting]:
        credentials = COMEET_BOARDS.get(board_token)
        if not credentials:
            raise ValueError(
                f"comeet/{board_token}: no uid/token in boards.py — "
                "add it with tools/find_comeet.py"
            )
        uid, token = credentials
        payload = fetch_json(
            self._client,
            API.format(uid=uid),
            {"token": token, "details": "true"},
        )
        if not isinstance(payload, list):
            raise ValueError(f"comeet/{board_token}: unexpected payload shape")
        for job in payload:
            # Internal-only postings are not open positions; counting them
            # would overstate the market.
            if job.get("is_internal"):
                continue
            yield self._to_posting(board_token, job)

    def _to_posting(self, board_token: str, job: dict[str, Any]) -> Posting:
        return Posting(
            source=self.name,
            board_token=board_token,
            external_id=str(job.get("uid") or ""),
            company=(job.get("company_name") or board_token).strip(),
            title=(job.get("name") or "").strip(),
            location_raw=_location(job),
            department=(job.get("department") or "").strip(),
            description=_description(job),
            # `position_url` carries the API token in a query parameter, so the
            # public hosted page is stored instead — a stored URL may end up
            # in published output.
            url=(job.get("url_comeet_hosted_page")
                 or job.get("url_active_page") or "").strip(),
            # Comeet publishes no creation timestamp, only the last update, so
            # posted_at stays empty rather than being filled with a wrong date.
            posted_at=None,
            ats_updated_at=_parse_ts(job.get("time_updated")),
            raw=job,
        )
