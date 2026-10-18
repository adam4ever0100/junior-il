"""Source protocol and the HTTP behaviour every source must share."""
import time
from typing import Any, Iterable, Optional, Protocol

import httpx

from junior_il.models import Posting

# Big boards occasionally time out on the first request and answer fine on the
# second. Retrying beats recording a false "board down".
RETRIES = 3
BACKOFF_SECONDS = 2.0


class Source(Protocol):
    name: str

    def fetch(self, board_token: str) -> Iterable[Posting]:
        """Return every posting currently on the board.

        Must raise on a partial or failed fetch rather than returning a short
        list: the caller treats a successful return as the complete board and
        closes anything missing from it.
        """
        ...


def fetch_json(
    client: httpx.Client, url: str, params: Optional[dict[str, Any]] = None
) -> Any:
    """GET and decode JSON, retrying transient failures but never a 404.

    The 404 rule is load-bearing beyond this function: a timeout is temporary,
    so postings must not be closed because of one, while a 404 means the board
    is gone and `retire-boards` should close its postings. Treating the two
    alike would either invent a hiring slowdown or leave dead jobs open
    forever, so the distinction is made once, here.
    """
    last: Optional[Exception] = None
    for attempt in range(RETRIES):
        try:
            response = client.get(url, params=params)
            response.raise_for_status()
            return response.json()
        except (httpx.TransportError, httpx.HTTPStatusError) as exc:
            if isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code == 404:
                raise
            last = exc
            if attempt < RETRIES - 1:
                time.sleep(BACKOFF_SECONDS * (attempt + 1))
    raise last  # type: ignore[misc]
