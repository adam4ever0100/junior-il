"""Source protocol — add an ATS by implementing fetch()."""
from typing import Iterable, Protocol

from junior_il.models import Posting


class Source(Protocol):
    name: str

    def fetch(self, board_token: str) -> Iterable[Posting]:
        """Return every posting currently on the board.

        Must raise on a partial or failed fetch rather than returning a short
        list: the caller treats a successful return as the complete board and
        closes anything missing from it.
        """
        ...
