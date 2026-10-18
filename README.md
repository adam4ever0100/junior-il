# junior-il

**How much of the Israeli tech market is actually open to a graduate with no
professional experience?**

Nobody publishes that number. Advice to Israeli CS graduates — learn X, apply
everywhere, keep trying — is not backed by any public measurement, and the
companies themselves do not report it. So this project measures it: open
engineering roles at Israeli companies, pulled from the companies' own public
ATS job boards, normalized, and published as a repeatable index.

It is market analytics, not a job board and not an application bot.

## What it found

Measured **23 September 2026** across **20 Israeli company job boards**
(19 returned postings; At-Bay's board was live but empty), **900 open postings**,
**192 of them located in Israel**:

| | |
|---|---|
| Open roles located in Israel | **192** |
| With a junior / graduate / student / intern title | **1** — and it was *Employer Branding Student*, not engineering |
| Explicitly asking for 3+ years of experience | **135 of 192** |

Companies sampled: AppsFlyer, At-Bay, Augury, Bringg, Cato Networks,
Cybereason, Fireblocks, Island, JFrog, Lightricks, Melio, NICE, Optimove,
Orca Security, Pagaya, Riskified, Similarweb, Taboola, Via, Yotpo.

That is the finding the rest of this project exists to keep measuring: whether
the junior door at Israeli product companies stays shut, and which parts of the
market are open instead.

The exact query behind these numbers is being moved out of ad-hoc SQL and into
code (`junior-il index`, with the rules written up in `METHOD.md`) so that
anyone can reproduce or contest them. See [PLAN.md](PLAN.md).

## Status

| Stage | What | State |
|---|---|---|
| 1 | Ingest: public ATS boards → Postgres | **done** |
| 2 | Normalizer: location, seniority, minimum years, Hebrew titles | in progress |
| 3 | The index: reproducible snapshots + published method | next |
| 4 | Public page, scheduled updates, CI | next |
| 5 | Read API (Java 21 / Spring Boot) over the normalized data | after launch |

## How the numbers are kept honest

These are the decisions that matter more than the stack, because the usual way
a job-market dataset goes wrong is quietly:

- **A failed fetch is not an empty board.** `Source.fetch()` raises rather than
  returning a short list, and postings are only marked closed after a fully
  successful fetch — otherwise one network timeout would fabricate a hiring
  slowdown in the charts. This is not hypothetical: the 23 September sweep hit
  a `ReadTimeout` on one board.
- **Every run is recorded.** `ingest_run` separates "no junior roles this week"
  from "the poller was broken this week". An index snapshot computed from an
  incomplete sweep is labelled as such.
- **Raw data is never lost.** Postings are stored verbatim, with the full JSON
  payload, before any parsing. Normalization is a separate stage, so a parser
  bug never destroys a day of collection.
- **Polls are idempotent.** `content_hash` means re-ingesting an unchanged
  posting only moves `last_seen_at`; `content_changed_at` moves only on a real
  edit.
- **One bad board does not stop the run.** Failures are isolated per board,
  recorded, and retried with backoff — except 404s, which retrying cannot fix.
- **Aggregates are published, not other people's job descriptions.** The raw
  text stays in the database; the published output is counts, percentages and
  links back to the employer.

## Limits of the sample

Stated up front, because a number is only worth quoting if you know what it
cannot see:

- Greenhouse boards only so far. Comeet (widely used in Israel) is next.
  Workday employers, agencies, and roles posted on LinkedIn alone are absent.
- 20 companies is a sample, not a census, and it is weighted toward product
  companies — which is exactly the tier the finding above is about.
- Boards are polled politely and infrequently; this is not a real-time feed.

## Running it

```bash
docker compose up -d                       # Postgres 17 on :55432, schema auto-applied
cd ingest
python3.13 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt
.venv/bin/python -m junior_il.cli ingest   # poll every board
.venv/bin/python -m junior_il.cli stats    # what landed
cd .. && ingest/.venv/bin/python -m pytest -q
```

Stack: Python 3.13 (httpx + psycopg3, no ORM), Postgres 17, Docker Compose.

## Adding a source

Implement `fetch(board_token) -> Iterable[Posting]` (see
`junior_il/sources/base.py`) and register it in `junior_il/sources/__init__.py`.
New boards go in `junior_il/boards.py` — in code rather than the database,
because "who counts as an Israeli employer" is a reviewed decision.

## Who built it

Adam Abu Saad — B.Sc. Computer Science, Shamoon College of Engineering (SCE),
graduating June 2026. I started measuring this market because I am in it, and
the data I wanted did not exist.

Corrections and additional boards are welcome — open an issue.
adamabusaad@gmail.com
