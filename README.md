# junior-il

**What do Israeli tech companies actually ask juniors for?**

A live dataset of open engineering roles at Israeli companies, ingested from
public ATS APIs, normalized, and published as an API and dashboard.

Built because the advice given to Israeli CS graduates ("learn X, apply
everywhere") is not backed by data. This measures the market instead.

## Status

| Stage | What | State |
|---|---|---|
| 1 | Ingest: Greenhouse boards → Postgres | **done** |
| 2 | Normalizer + REST API (Java / Spring Boot) | next |
| 3 | Dashboard, deploy, Prometheus + Grafana, CI | planned |

## First finding

From 21 Israeli company boards, 900 open postings, 192 of them in Israel:

- **1** posting has a junior / graduate / student title — and it is not engineering.
- **135 of 192** explicitly ask for 3+ years of experience.

The junior door at Israeli product companies is close to shut. That number is
the reason this project exists.

## Running it

```bash
docker compose up -d                       # Postgres on :55432, schema auto-applied
cd ingest
python3.13 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt
.venv/bin/python -m junior_il.cli ingest   # poll every board
.venv/bin/python -m junior_il.cli stats    # what landed
.venv/bin/python -m pytest tests -q
```

## Design notes

- **Raw data is never lost.** Sources write postings verbatim (plus the full
  JSON payload) into `posting`. Normalization is a later stage, so a parser
  bug never destroys a day of collection.
- **A failed fetch is not an empty board.** `Source.fetch()` raises rather than
  returning a short list, and postings are only marked closed after a fully
  successful fetch — otherwise a network timeout would fabricate a hiring
  slowdown in the charts.
- **Every run is recorded.** `ingest_run` separates "no junior roles this week"
  from "the poller was broken this week".
- **Polls are idempotent.** `content_hash` means re-ingesting an unchanged
  posting only moves `last_seen_at`; `content_changed_at` moves only on a real
  edit.
- **One bad board does not stop the run.** Failures are isolated per board,
  recorded, and retried with backoff (except 404s, which retrying cannot fix).

## Adding a source

Implement `fetch(board_token) -> Iterable[Posting]` (see
`junior_il/sources/base.py`) and register it in `junior_il/sources/__init__.py`.
