"""Postgres access. Small and explicit — no ORM."""
import hashlib
from contextlib import contextmanager
from dataclasses import asdict, dataclass
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


# --- normalization -------------------------------------------------------

POSTING_COLUMNS = "id, source, board_token, company, title, location_raw, department, description, url"


def iter_postings(
    conn: psycopg.Connection, only_open: bool = True, batch: int = 500
) -> Iterator[dict]:
    """Stream postings for normalization, so a 1200-row corpus (or a 100k one
    later) never has to be held in memory at once."""
    where = "WHERE closed_at IS NULL" if only_open else ""
    with conn.cursor(name="postings_cursor") as cur:
        cur.itersize = batch
        cur.execute(f"SELECT {POSTING_COLUMNS} FROM posting {where} ORDER BY id")
        yield from cur


UPSERT_NORM = """
INSERT INTO posting_norm (
    posting_id, parser_version, normalized_at, is_israel, il_cities, is_remote,
    is_engineering, seniority, junior_signal, years_stated, years_vague, years_floor,
    years_bar, years_evidence, degree_required, clearance_required,
    junior_eligible
) VALUES (
    %(posting_id)s, %(parser_version)s, now(), %(is_israel)s, %(il_cities)s,
    %(is_remote)s, %(is_engineering)s, %(seniority)s, %(junior_signal)s,
    %(years_stated)s, %(years_vague)s, %(years_floor)s, %(years_bar)s, %(years_evidence)s,
    %(degree_required)s, %(clearance_required)s, %(junior_eligible)s
)
ON CONFLICT (posting_id) DO UPDATE SET
    parser_version = EXCLUDED.parser_version,
    normalized_at  = now(),
    is_israel      = EXCLUDED.is_israel,
    il_cities      = EXCLUDED.il_cities,
    is_remote      = EXCLUDED.is_remote,
    is_engineering = EXCLUDED.is_engineering,
    seniority      = EXCLUDED.seniority,
    junior_signal  = EXCLUDED.junior_signal,
    years_stated   = EXCLUDED.years_stated,
    years_vague    = EXCLUDED.years_vague,
    years_floor    = EXCLUDED.years_floor,
    years_bar      = EXCLUDED.years_bar,
    years_evidence = EXCLUDED.years_evidence,
    degree_required    = EXCLUDED.degree_required,
    clearance_required = EXCLUDED.clearance_required,
    junior_eligible    = EXCLUDED.junior_eligible
"""


def upsert_norm(conn: psycopg.Connection, rows: Iterable) -> int:
    """Write normalized rows. Takes NormalizedPosting dataclasses."""
    count = 0
    with conn.cursor() as cur:
        for row in rows:
            cur.execute(UPSERT_NORM, asdict(row))
            count += 1
    return count


def reparse_descriptions(conn: psycopg.Connection, parse) -> tuple[int, int]:
    """Re-derive `posting.description` from the stored raw payload.

    Needed because the first ingest stored descriptions that still contained
    literal markup: Greenhouse sends HTML-escaped HTML, so one stripping pass
    turned "&lt;li&gt;" into the text "<li>" instead of a line break. No
    re-fetch is required — the untouched ATS payload is in `posting.raw`, which
    is the whole reason it is kept.

    `content_changed_at` is deliberately left alone. Our parser improving is
    not the employer editing the posting, and moving it would show up as a wave
    of fake edits on exactly the date the bug was fixed.
    """
    checked = changed = 0
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id, title, location_raw, department, url, description,"
            "       raw->>'content' AS raw_content"
            "  FROM posting WHERE raw->>'content' IS NOT NULL ORDER BY id"
        )
        rows = cur.fetchall()
        for row in rows:
            checked += 1
            fresh = parse(row["raw_content"] or "")
            if fresh == row["description"]:
                continue
            digest = hashlib.sha256(
                "\x1f".join([
                    row["title"], row["location_raw"], row["department"],
                    fresh, row["url"],
                ]).encode("utf-8")
            ).hexdigest()
            cur.execute(
                "UPDATE posting SET description = %s, content_hash = %s WHERE id = %s",
                (fresh, digest, row["id"]),
            )
            changed += 1
    return checked, changed


# --- board health & retirement -------------------------------------------

def latest_run_per_board(conn: psycopg.Connection) -> list[dict]:
    """The most recent poll of each board, with its status and error."""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT DISTINCT ON (source, board_token)
                   source, board_token, status, started_at, error
              FROM ingest_run
             ORDER BY source, board_token, started_at DESC
        """)
        return cur.fetchall()


def retire_dead_boards(conn: psycopg.Connection, boards: list[tuple[str, str]]) -> dict[str, int]:
    """Close postings belonging to boards that have ceased to exist.

    A 404 is not a timeout. Postings are normally closed only after a
    successful fetch, which is right when a poll fails transiently — but a
    board that has been removed never fetches successfully again, so its
    postings would stay 'open' forever and quietly inflate every later count.
    Cybereason's Greenhouse board disappeared between the September and October
    sweeps; this is the rule that keeps its five postings out of the index.
    """
    closed: dict[str, int] = {}
    for source, board_token in boards:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT status, error FROM ingest_run
                 WHERE source = %s AND board_token = %s
                 ORDER BY started_at DESC LIMIT 1
            """, (source, board_token))
            run = cur.fetchone()
            if not run or run["status"] == "ok" or "404" not in (run["error"] or ""):
                continue
            cur.execute("""
                UPDATE posting
                   SET closed_at = now(), closed_reason = 'board_retired'
                 WHERE source = %s AND board_token = %s AND closed_at IS NULL
            """, (source, board_token))
            if cur.rowcount:
                closed[f"{source}/{board_token}"] = cur.rowcount
    return closed


# --- index ---------------------------------------------------------------

def unnormalized_open(conn: psycopg.Connection, parser_version: str) -> int:
    """Open postings with no normalized row for this parser version.

    The index must never be computed over a half-normalized corpus: the
    missing rows would silently read as "not in Israel".
    """
    with conn.cursor() as cur:
        cur.execute("""
            SELECT count(*) AS n
              FROM posting p
              LEFT JOIN posting_norm n
                     ON n.posting_id = p.id AND n.parser_version = %s
             WHERE p.closed_at IS NULL AND n.posting_id IS NULL
        """, (parser_version,))
        return cur.fetchone()["n"]


INDEX_COUNTS = """
SELECT
  count(*)                                                        AS open_total,
  count(*) FILTER (WHERE n.is_israel)                             AS open_israel,
  count(*) FILTER (WHERE n.is_israel AND n.is_engineering)         AS open_israel_eng,
  count(*) FILTER (WHERE n.junior_eligible)                        AS junior_eligible,
  count(*) FILTER (WHERE n.is_israel AND n.is_engineering
                     AND n.years_stated AND n.years_bar <= 1)      AS explicit_entry,
  count(*) FILTER (WHERE n.is_israel AND n.is_engineering
                     AND n.years_bar >= 3)                         AS bar_3plus,
  count(*) FILTER (WHERE n.is_israel AND n.is_engineering
                     AND NOT n.years_stated AND NOT n.years_vague) AS years_unstated,
  count(*) FILTER (WHERE n.is_israel AND n.is_engineering
                     AND n.years_vague)                            AS years_vague,
  count(*) FILTER (WHERE n.is_israel AND n.junior_signal)          AS junior_titled,
  count(*) FILTER (WHERE n.is_israel AND n.is_engineering
                     AND n.degree_required)                        AS degree_required,
  count(*) FILTER (WHERE n.is_israel AND n.is_engineering
                     AND n.clearance_required)                     AS clearance_required
FROM posting p
JOIN posting_norm n ON n.posting_id = p.id AND n.parser_version = %s
WHERE p.closed_at IS NULL
"""


def index_counts(conn: psycopg.Connection, parser_version: str) -> dict:
    with conn.cursor() as cur:
        cur.execute(INDEX_COUNTS, (parser_version,))
        return cur.fetchone()


def years_histogram(conn: psycopg.Connection, parser_version: str) -> list[dict]:
    """Israeli engineering roles bucketed by the bar they set."""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT CASE
                     WHEN n.years_vague THEN 'unquantified'
                     WHEN NOT n.years_stated THEN 'unstated'
                     WHEN n.years_bar <= 1 THEN '0-1'
                     WHEN n.years_bar = 2 THEN '2'
                     WHEN n.years_bar BETWEEN 3 AND 4 THEN '3-4'
                     ELSE '5+'
                   END AS bucket,
                   count(*) AS roles
              FROM posting p
              JOIN posting_norm n ON n.posting_id = p.id AND n.parser_version = %s
             WHERE p.closed_at IS NULL AND n.is_israel AND n.is_engineering
             GROUP BY 1
        """, (parser_version,))
        return cur.fetchall()


def insert_snapshot(conn: psycopg.Connection, fields: dict) -> int:
    columns = ", ".join(fields)
    placeholders = ", ".join(f"%({k})s" for k in fields)
    with conn.cursor() as cur:
        cur.execute(
            f"INSERT INTO index_snapshot ({columns}) VALUES ({placeholders}) RETURNING id",
            fields,
        )
        return cur.fetchone()["id"]


def snapshot_series(conn: psycopg.Connection, limit: int = 24) -> list[dict]:
    with conn.cursor() as cur:
        cur.execute("""
            SELECT taken_at, status, open_israel_eng, junior_eligible,
                   pct_junior_eligible, bar_3plus, parser_version
              FROM index_snapshot ORDER BY taken_at DESC LIMIT %s
        """, (limit,))
        return cur.fetchall()


def company_breakdown(conn: psycopg.Connection, parser_version: str) -> list[dict]:
    """Israeli engineering roles per company, with the junior picture."""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT p.company,
                   count(*)                                        AS il_eng,
                   count(*) FILTER (WHERE n.junior_eligible)        AS eligible,
                   count(*) FILTER (WHERE n.years_bar >= 3)         AS bar_3plus,
                   count(*) FILTER (WHERE n.years_bar >= 5)         AS bar_5plus
              FROM posting p
              JOIN posting_norm n ON n.posting_id = p.id
                                 AND n.parser_version = %s
             WHERE p.closed_at IS NULL AND n.is_israel AND n.is_engineering
             GROUP BY p.company
             ORDER BY il_eng DESC, p.company
        """, (parser_version,))
        return cur.fetchall()


def eligible_roles(conn: psycopg.Connection, parser_version: str) -> list[dict]:
    """The roles a graduate can actually apply to, with links to the employer.

    Only title, company, location and the employer's own URL — never the
    description text, which belongs to whoever wrote it.
    """
    with conn.cursor() as cur:
        cur.execute("""
            SELECT p.company, p.title, p.location_raw, p.url, p.source
              FROM posting p
              JOIN posting_norm n ON n.posting_id = p.id
                                 AND n.parser_version = %s
             WHERE p.closed_at IS NULL AND n.junior_eligible
             ORDER BY p.company, p.title
        """, (parser_version,))
        return cur.fetchall()
