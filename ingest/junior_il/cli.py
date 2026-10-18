"""Command line entry point: python -m junior_il.cli <command>"""
import argparse
import logging
import sys
from pathlib import Path

from junior_il import db
from junior_il.boards import ALL_BOARDS
from junior_il.htmltext import html_to_text
from junior_il.ingest import ingest_all
from junior_il.normalize import PARSER_VERSION, normalize_posting

SQL_DIR = Path(__file__).resolve().parents[2] / "sql"
SCHEMA_FILES = ("001_schema.sql", "002_normalize.sql")


def cmd_initdb(args) -> int:
    with db.connect(args.dsn) as conn:
        for name in SCHEMA_FILES:
            db.apply_schema(conn, str(SQL_DIR / name))
            print(f"applied {name}")
    return 0


def cmd_reparse(args) -> int:
    """Re-derive descriptions from the stored raw payload, no network."""
    with db.connect(args.dsn) as conn:
        checked, changed = db.reparse_descriptions(conn, html_to_text)
    print(f"{changed}/{checked} descriptions rewritten from raw payload")
    if changed:
        print("re-run `normalize` so the rules see the corrected text")
    return 0


def cmd_normalize(args) -> int:
    with db.connect(args.dsn) as conn:
        rows = (normalize_posting(row) for row in db.iter_postings(conn, only_open=not args.all))
        written = db.upsert_norm(conn, rows)
    scope = "all" if args.all else "open"
    print(f"normalized {written} {scope} postings with parser {PARSER_VERSION}")
    return 0


def cmd_ingest(args) -> int:
    boards = ALL_BOARDS
    if args.board:
        boards = [b for b in boards if b[1] in args.board]
        missing = set(args.board) - {b[1] for b in boards}
        if missing:
            print(f"unknown board(s): {', '.join(sorted(missing))}", file=sys.stderr)
            return 2
    with db.connect(args.dsn) as conn:
        results = ingest_all(conn, boards)

    failed = [r for r in results if r.status != "ok"]
    total = sum(r.stats.fetched for r in results)
    print(
        f"\n{len(results) - len(failed)}/{len(results)} boards ok, "
        f"{total} postings seen"
    )
    for result in failed:
        print(f"  FAILED {result.source}/{result.board_token}: {result.error}")
    # Partial success is still success for a scheduled run; only a total
    # wipeout is worth a non-zero exit.
    return 1 if failed and len(failed) == len(results) else 0


def cmd_stats(args) -> int:
    with db.connect(args.dsn) as conn:
        rows = conn.execute("""
            SELECT company,
                   count(*) FILTER (WHERE closed_at IS NULL) AS open_roles,
                   count(*) AS all_time
              FROM posting
             GROUP BY company
             ORDER BY open_roles DESC
        """).fetchall()
        totals = conn.execute("""
            SELECT count(*) AS n,
                   count(*) FILTER (WHERE closed_at IS NULL) AS open
              FROM posting
        """).fetchone()
    print(f"{'company':28} {'open':>6} {'all time':>9}")
    for row in rows:
        print(f"{row['company'][:28]:28} {row['open_roles']:>6} {row['all_time']:>9}")
    print(f"\n{totals['open']} open / {totals['n']} total postings")
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="junior-il")
    parser.add_argument("--dsn", default=None, help="Postgres DSN")
    parser.add_argument("-v", "--verbose", action="store_true")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("initdb", help="create tables").set_defaults(func=cmd_initdb)

    ingest = sub.add_parser("ingest", help="poll boards")
    ingest.add_argument("--board", action="append", help="limit to this board token")
    ingest.set_defaults(func=cmd_ingest)

    sub.add_parser("stats", help="what is in the database").set_defaults(func=cmd_stats)

    sub.add_parser(
        "reparse", help="rebuild descriptions from stored raw payloads"
    ).set_defaults(func=cmd_reparse)

    normalize = sub.add_parser("normalize", help="derive posting_norm from posting")
    normalize.add_argument(
        "--all", action="store_true",
        help="include closed postings (default: only those still open)",
    )
    normalize.set_defaults(func=cmd_normalize)

    args = parser.parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
