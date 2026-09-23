"""The one shape every source must produce."""
import hashlib
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional


@dataclass(slots=True)
class Posting:
    source: str
    board_token: str
    external_id: str
    company: str
    title: str
    location_raw: str = ""
    department: str = ""
    description: str = ""
    url: str = ""
    posted_at: Optional[datetime] = None
    ats_updated_at: Optional[datetime] = None
    raw: dict[str, Any] = field(default_factory=dict)

    def content_hash(self) -> str:
        """Hash of the fields that matter, so re-ingesting an unchanged posting
        is a no-op and `last_seen_at` is the only thing that moves."""
        parts = [
            self.title,
            self.location_raw,
            self.department,
            self.description,
            self.url,
        ]
        digest = hashlib.sha256("\x1f".join(parts).encode("utf-8"))
        return digest.hexdigest()
