# junior-il

### → **[adam4ever0100.github.io/junior-il](https://adam4ever0100.github.io/junior-il/)**

**How much of the Israeli tech market is actually open to a graduate with no
professional experience?**

Nobody publishes that number. Advice to Israeli CS graduates — learn X, apply
everywhere, keep trying — is not backed by any public measurement, and the
companies themselves do not report it. So this project measures it: open
engineering roles at Israeli companies, pulled from the companies' own public
ATS job boards, normalized, and published as a repeatable index.

It is market analytics, not a job board and not an application bot.

## What it found

Snapshot of **18 October 2026**, from **24 Israeli company job boards**
on Greenhouse and Comeet, **956 open postings**:

| | |
|---|---|
| Open roles located in Israel | **228** |
| …that are engineering | **137** |
| …whose stated bar is 3+ years | **123 of 137** |
| …open to a graduate with no experience | **4** (2.9%) |
| …that actually invite 0-1 years | **1** |
| …requiring a degree | **51** |
| Junior-titled roles in Israel, any field | **1** — *Employer Branding Student*, not engineering |

Read the fourth and fifth rows together, because that pair says more than the
headline: four roles can be applied to, but only **one** states a bar a
graduate could clear. The other three qualify by mentioning no requirement at
all. Most of the open door is an omission rather than an invitation.

These numbers change on every run — the page is generated from the database,
never written by hand.

A finding of its own: **searching for the word "Israel" does not find the
Israeli market.** Only about 58% of those roles contain "Israel" anywhere in the
location field — `Tel Aviv` alone is the most common value. Any analysis built
on a country-name filter is missing about 42% of the market.

Companies sampled: AppsFlyer, At-Bay, Augury, Bringg, Cato Networks, Cycode,
Fireblocks, Gloat, Island, JFrog, Lightricks, Melio, NICE, Optimove,
Orca Security, Pagaya, Pentera, Riskified, Similarweb, Taboola, Tastewise,
Via, Yotpo, Zesty.

**On coverage:** adding Comeet was meant to roughly double the Israeli sample
and did not. Most larger Israeli companies checked are elsewhere — Ashby,
Workday — so the next ATS worth adding is one of those, not more Comeet.
`tools/find_comeet.py` and `tools/find_greenhouse.py` read a company's own
careers page and verify a board against the live API before it is added;
guessing identifiers does not work.

Every definition behind these numbers — what counts as Israel, as engineering,
as a years requirement — is written down in **[METHOD.md](METHOD.md)**, along
with the limits of the sample and the specific wrong numbers this pipeline
refuses to produce. Errors in the method are worth more to me than agreement
with the conclusions.

### Earlier measurement

23 September 2026, same boards: 192 roles in Israel, 1 junior-titled, 135
asking 3+ years. Those figures predate the normalizer and are not directly
comparable — they came from ad-hoc SQL over descriptions that still contained
unstripped markup. The October numbers are the first produced by code.

## Status

| Stage | What | State |
|---|---|---|
| 1 | Ingest: public ATS boards → Postgres | **done** |
| 2 | Normalizer: location, seniority, experience bar, Hebrew titles | **done** |
| 3 | The index: reproducible snapshots + published method | **done** |
| 4 | Public page, scheduled updates, CI | **done** |
| 5 | Comeet source | **done** — 5 boards; see note below |
| 6 | Read API (Java 21 / Spring Boot) over the normalized data | after launch |

82 tests, no network required. `pytest` from the repo root.

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
docker compose up -d                            # Postgres 17 on :55432
cd ingest
python3.13 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt
.venv/bin/python -m junior_il.cli initdb
.venv/bin/python -m junior_il.cli ingest        # poll every board
.venv/bin/python -m junior_il.cli retire-boards # close boards that vanished
.venv/bin/python -m junior_il.cli normalize     # derive posting_norm
.venv/bin/python -m junior_il.cli index         # the index, printed
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
