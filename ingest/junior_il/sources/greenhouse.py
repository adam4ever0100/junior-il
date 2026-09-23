"""Greenhouse job board API.

One request per board returns every open posting with its full description:
    https://boards-api.greenhouse.io/v1/boards/{token}/jobs?content=true
No key, no pagination, no anti-bot. This is why it is the first source.
"""
import time
from datetime import datetime
from typing import Any, Iterator, Optional

import httpx

from junior_il import config
from junior_il.htmltext import html_to_text
from junior_il.models import Posting

API = "https://boards-api.greenhouse.io/v1/boards/{token}/jobs"

# Big boards occasionally time out on the first request and answer fine on the
# second. Retrying beats recording a false "board down".
RETRIES = 3
BACKOFF_SECONDS = 2.0


def _parse_ts(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


class GreenhouseSource:
    name = "greenhouse"

    def __init__(self, client: Optional[httpx.Client] = None) -> None:
        self._client = client or httpx.Client(
            timeout=config.REQUEST_TIMEOUT,
            headers={"User-Agent": config.USER_AGENT},
            follow_redirects=True,
        )

    def fetch(self, board_token: str) -> Iterator[Posting]:
        payload = self._get_with_retry(board_token)
        jobs = payload.get("jobs")
        if not isinstance(jobs, list):
            raise ValueError(f"greenhouse/{board_token}: unexpected payload shape")
        for job in jobs:
            yield self._to_posting(board_token, job)

    def _get_with_retry(self, board_token: str) -> dict[str, Any]:
        last: Exception | None = None
        for attempt in range(RETRIES):
            try:
                response = self._client.get(
                    API.format(token=board_token), params={"content": "true"}
                )
                response.raise_for_status()
                return response.json()
            except (httpx.TransportError, httpx.HTTPStatusError) as exc:
                # A 404 means the board token is wrong; retrying cannot fix it.
                if isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code == 404:
                    raise
                last = exc
                if attempt < RETRIES - 1:
                    time.sleep(BACKOFF_SECONDS * (attempt + 1))
        raise last  # type: ignore[misc]

    def _to_posting(self, board_token: str, job: dict[str, Any]) -> Posting:
        departments = job.get("departments") or []
        department = departments[0].get("name", "") if departments else ""
        # company_name is per-posting on Greenhouse and is occasionally blank
        # for boards that never set it; the token is a usable fallback.
        company = (job.get("company_name") or board_token).strip()
        return Posting(
            source=self.name,
            board_token=board_token,
            external_id=str(job.get("id")),
            company=company,
            title=(job.get("title") or "").strip(),
            location_raw=((job.get("location") or {}).get("name") or "").strip(),
            department=department,
            description=html_to_text(job.get("content") or ""),
            url=job.get("absolute_url") or "",
            posted_at=_parse_ts(job.get("first_published")),
            ats_updated_at=_parse_ts(job.get("updated_at")),
            raw=job,
        )
