"""Postgres access. Small and explicit — no ORM."""
import json
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Iterable, Iterator, Optional

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from junior_il import config
from junior_il.models import Posting


@dataclass
class UpsertStats:
    fetched: int = 0
    inserted: int = 0
    updated: int = 0      # seen again, content had really changed
    unchanged: int = 0    # seen again, byte-identical
    closed: int = 0


@contextmanager
def connect(dsn: Optional[str] = None) -> Iterator[psycopg.Connection]:
    conn = psycopg.connect(dsn or config.DSN, row_factory=dict_row)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def apply_schema(conn: psycopg.Connection, sql_path: str) -> None:
    with open(sql_path, encoding="utf-8") as handle:
        conn.execute(handle.read())


UPSERT = """
INSERT INTO posting (
    source, board_token, external_id, company, title, location_raw,
    department, description, url, posted_at, ats_updated_at,
    content_hash, content_changed_at, raw, first_seen_at, last_seen_at, closed_at
) VALUES (
    %(source)s, %(board_token)s, %(external_id)s, %(company)s, %(title)s,
    %(location_raw)s, %(department)s, %(description)s, %(url)s, %(posted_at)s,
    %(ats_updated_at)s, %(content_hash)s, now(), %(raw)s, now(), now(), NULL
)
ON CONFLICT (source, board_token, external_id) DO UPDATE SET
    company        = EXCLUDED.company,
    title          = EXCLUDED.title,
    location_raw   = EXCLUDED.location_raw,
    department     = EXCLUDED.department,
    description    = EXCLUDED.description,
    url            = EXCLUDED.url,
    posted_at      = EXCLUDED.posted_at,
    ats_updated_at = EXCLUDED.ats_updated_at,
    content_hash   = EXCLUDED.content_hash,
    raw            = EXCLUDED.raw,
    last_seen_at   = now(),
    -- only moves when the posting text actually changed, so "edited" charts
    -- do not light up every time the poller runs
    content_changed_at = CASE
        WHEN posting.content_hash IS DISTINCT FROM EXCLUDED.content_hash THEN now()
        ELSE posting.content_changed_at
    END,
    -- a posting that reappears on the board is open again
    closed_at      = NULL
-- RETURNING sees the NEW row, so the old hash is unreachable here; comparing
-- content_changed_at against the run start is how we tell a real edit apart
-- from a no-op refresh.
RETURNING (xmax = 0) AS was_insert, content_changed_at
"""


def upsert_postings(
    conn: psycopg.Connection, postings: Iterable[Posting]
) -> tuple[UpsertStats, list[str]]:
    """Insert or refresh postings. Returns stats and the external ids seen."""
    stats = UpsertStats()
    seen: list[str] = []
    with conn.cursor() as cur:
        cur.execute("SELECT now() AS t")
        run_start = cur.fetchone()["t"]
        for posting in postings:
            stats.fetched += 1
            seen.append(posting.external_id)
            cur.execute(
                UPSERT,
                {
                    "source": posting.source,
                    "board_token": posting.board_token,
                    "external_id": posting.external_id,
                    "company": posting.company,
                    "title": posting.title,
                    "location_raw": posting.location_raw,
                    "department": posting.department,
                    "description": posting.description,
                    "url": posting.url,
                    "posted_at": posting.posted_at,
                    "ats_updated_at": posting.ats_updated_at,
                    "content_hash": posting.content_hash(),
                    "raw": Jsonb(posting.raw),
                },
            )
            row = cur.fetchone()
            if row and row["was_insert"]:
                stats.inserted += 1
            elif row and row["content_changed_at"] >= run_start:
                stats.updated += 1
            else:
                stats.unchanged += 1
    return stats, seen


CLOSE = """
UPDATE posting
   SET closed_at = now()
 WHERE source = %(source)s
   AND board_token = %(board_token)s
   AND closed_at IS NULL
   AND NOT (external_id = ANY(%(seen)s))
"""


def close_missing(
    conn: psycopg.Connection, source: str, board_token: str, seen: list[str]
) -> int:
    """Mark postings that vanished from the board as closed.

    Only called after a fully successful fetch — closing on a partial fetch
    would invent a hiring slowdown that never happened.
    """
    with conn.cursor() as cur:
        cur.execute(CLOSE, {"source": source, "board_token": board_token, "seen": seen})
        return cur.rowcount


def start_run(conn: psycopg.Connection, source: str, board_token: str) -> int:
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO ingest_run (source, board_token) VALUES (%s, %s) RETURNING id",
            (source, board_token),
        )
        return cur.fetchone()["id"]


def finish_run(
    conn: psycopg.Connection,
    run_id: int,
    status: str,
    stats: UpsertStats,
    error: Optional[str] = None,
) -> None:
    conn.execute(
        """
        UPDATE ingest_run
           SET finished_at = now(), status = %s, fetched = %s, inserted = %s,
               updated = %s, unchanged = %s, closed = %s, error = %s
         WHERE id = %s
        """,
        (status, stats.fetched, stats.inserted, stats.updated, stats.unchanged,
         stats.closed, error, run_id),
    )
