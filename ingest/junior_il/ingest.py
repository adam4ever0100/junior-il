"""Ingest orchestration: poll each board, record what happened."""
import logging
import time
from dataclasses import dataclass
from typing import Optional

from junior_il import config, db
from junior_il.sources import SOURCES

log = logging.getLogger("junior_il.ingest")


@dataclass
class BoardResult:
    source: str
    board_token: str
    status: str
    stats: db.UpsertStats
    error: Optional[str] = None


def ingest_board(conn, source_name: str, board_token: str) -> BoardResult:
    source = SOURCES[source_name]()
    run_id = db.start_run(conn, source_name, board_token)
    conn.commit()  # the run row must survive a later failure

    stats = db.UpsertStats()
    try:
        postings = list(source.fetch(board_token))
        stats, seen = db.upsert_postings(conn, postings)
        stats.closed = db.close_missing(conn, source_name, board_token, seen)
        db.finish_run(conn, run_id, "ok", stats)
        conn.commit()
        log.info(
            "%s/%s ok: fetched=%d new=%d changed=%d same=%d closed=%d",
            source_name, board_token, stats.fetched, stats.inserted,
            stats.updated, stats.unchanged, stats.closed,
        )
        return BoardResult(source_name, board_token, "ok", stats)
    except Exception as exc:  # one bad board must not stop the rest
        conn.rollback()
        message = f"{type(exc).__name__}: {exc}"[:2000]
        db.finish_run(conn, run_id, "error", stats, message)
        conn.commit()
        log.warning("%s/%s failed: %s", source_name, board_token, message)
        return BoardResult(source_name, board_token, "error", stats, message)


def ingest_all(conn, boards: list[tuple[str, str]]) -> list[BoardResult]:
    results = []
    for index, (source_name, board_token) in enumerate(boards):
        if index:
            time.sleep(config.DELAY_BETWEEN_BOARDS)
        results.append(ingest_board(conn, source_name, board_token))
    return results
