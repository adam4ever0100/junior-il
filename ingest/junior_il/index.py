"""The Junior Hiring Index: one number, computed the same way every time.

The number is the share of open engineering roles located in Israel that a
graduate with no professional experience can apply to without failing a stated
requirement. Everything that decides it lives in `normalize/`; this module only
counts, checks that the count is trustworthy, and records it.

Two guards exist because they are the ways a job-market index goes wrong
quietly rather than loudly:

* **Never count a half-normalized corpus.** A posting with no normalized row
  reads as "not in Israel", so the index would shrink for a reason that has
  nothing to do with hiring.
* **Never publish a partial sweep as a complete one.** A board that failed to
  answer is missing data, not an absence of jobs. Partial sweeps are still
  recorded — a hidden gap is worse than a labelled one.
"""
from dataclasses import dataclass
from typing import Optional

from junior_il import db
from junior_il.normalize import PARSER_VERSION

COMPLETE = "complete"
PARTIAL = "partial"


@dataclass(slots=True)
class BoardHealth:
    total: int
    ok: int
    retired: int
    failing: list[str]

    @property
    def status(self) -> str:
        # A retired board is accounted-for absence, not missing data: its
        # postings have been closed, so the corpus is still complete.
        return COMPLETE if self.ok + self.retired == self.total else PARTIAL


def board_health(conn, boards: list[tuple[str, str]]) -> BoardHealth:
    latest = {
        (row["source"], row["board_token"]): row
        for row in db.latest_run_per_board(conn)
    }
    ok = retired = 0
    failing: list[str] = []
    for source, token in boards:
        run = latest.get((source, token))
        if run and run["status"] == "ok":
            ok += 1
        elif run and "404" in (run["error"] or ""):
            retired += 1
        else:
            failing.append(f"{source}/{token}")
    return BoardHealth(total=len(boards), ok=ok, retired=retired, failing=failing)


class StaleNormalization(Exception):
    """Raised rather than publishing a number computed over missing rows."""


def compute(conn, boards: list[tuple[str, str]]) -> dict:
    pending = db.unnormalized_open(conn, PARSER_VERSION)
    if pending:
        raise StaleNormalization(
            f"{pending} open postings have no rows for parser {PARSER_VERSION} — "
            "run `junior-il normalize` first"
        )

    counts = dict(db.index_counts(conn, PARSER_VERSION))
    health = board_health(conn, boards)

    eligible = counts["junior_eligible"]
    denominator = counts["open_israel_eng"]
    counts.update(
        parser_version=PARSER_VERSION,
        status=health.status,
        boards_total=health.total,
        boards_ok=health.ok,
        boards_retired=health.retired,
        pct_junior_eligible=(
            round(100.0 * eligible / denominator, 2) if denominator else None
        ),
        notes=(
            "boards not answering: " + ", ".join(health.failing)
            if health.failing else None
        ),
    )
    return counts


def headline(counts: dict) -> str:
    """The one sentence the published page has to be able to generate."""
    return (
        f"Of {counts['open_israel_eng']} open engineering roles located in Israel "
        f"across {counts['boards_total']} company boards, "
        f"{counts['junior_eligible']} are open to a candidate with no "
        f"professional experience."
    )


def render(counts: dict, histogram: list[dict], series: Optional[list[dict]] = None) -> str:
    lines = [headline(counts), ""]
    pct = counts["pct_junior_eligible"]
    lines.append(f"  junior-eligible         {counts['junior_eligible']:>5}"
                 + (f"  ({pct}% of Israeli engineering roles)" if pct is not None else ""))
    lines.append(f"    of which invited        {counts['explicit_entry']:>5}"
                 "  (state a 0-1 year bar; the rest simply say nothing)")
    lines.append(f"  demanding 3+ years      {counts['bar_3plus']:>5}")
    lines.append(f"  junior-titled (Israel)  {counts['junior_titled']:>5}")
    lines.append(f"  degree required         {counts['degree_required']:>5}")
    lines.append(f"  clearance / IDF service {counts['clearance_required']:>5}")
    lines.append("")
    lines.append(f"  open postings, all boards  {counts['open_total']:>5}")
    lines.append(f"  located in Israel          {counts['open_israel']:>5}")
    lines.append(f"  of those, engineering      {counts['open_israel_eng']:>5}")
    lines.append("")

    order = ["0-1", "2", "3-4", "5+", "unquantified", "unstated"]
    buckets = {row["bucket"]: row["roles"] for row in histogram}
    lines.append("  experience bar, Israeli engineering roles")
    for key in order:
        if key in buckets:
            bar = "#" * min(40, buckets[key])
            lines.append(f"    {key:<13}{buckets[key]:>4}  {bar}")
    lines.append("")
    lines.append(f"  sweep: {counts['status']} "
                 f"({counts['boards_ok']}/{counts['boards_total']} boards answered, "
                 f"{counts['boards_retired']} retired)")
    if counts.get("notes"):
        lines.append(f"  {counts['notes']}")
    lines.append(f"  parser: {counts['parser_version']}")

    if series:
        lines.append("")
        lines.append("  previous snapshots")
        for row in series:
            lines.append(
                f"    {row['taken_at']:%Y-%m-%d}  {row['junior_eligible']:>3} of "
                f"{row['open_israel_eng']:>4}  ({row['pct_junior_eligible']}%)  "
                f"{row['status']}"
            )
    return "\n".join(lines)
