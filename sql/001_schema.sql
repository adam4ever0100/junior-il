-- junior-il: raw ingest schema.
-- Postings land here exactly as the ATS returned them; normalization is a
-- separate stage so a parser bug never costs us the source data.

CREATE TABLE IF NOT EXISTS posting (
    id              BIGSERIAL PRIMARY KEY,
    source          TEXT        NOT NULL,          -- 'greenhouse', 'comeet', ...
    board_token     TEXT        NOT NULL,          -- board slug on that ATS
    external_id     TEXT        NOT NULL,          -- id within the ATS
    company         TEXT        NOT NULL,
    title           TEXT        NOT NULL,
    location_raw    TEXT        NOT NULL DEFAULT '',
    department      TEXT        NOT NULL DEFAULT '',
    description     TEXT        NOT NULL DEFAULT '',  -- plain text, tags stripped
    url             TEXT        NOT NULL DEFAULT '',
    posted_at       TIMESTAMPTZ,
    ats_updated_at  TIMESTAMPTZ,
    content_hash    TEXT        NOT NULL,          -- sha256 of the fields above
    content_changed_at TIMESTAMPTZ NOT NULL DEFAULT now(),  -- last real edit, not last poll
    raw             JSONB       NOT NULL,
    first_seen_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_seen_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    closed_at       TIMESTAMPTZ,                   -- set when it drops off the board
    UNIQUE (source, board_token, external_id)
);

CREATE INDEX IF NOT EXISTS posting_company_idx    ON posting (company);
CREATE INDEX IF NOT EXISTS posting_last_seen_idx  ON posting (last_seen_at DESC);
CREATE INDEX IF NOT EXISTS posting_open_idx       ON posting (closed_at) WHERE closed_at IS NULL;

-- One row per ingest run, so we can tell "no junior jobs this week" apart from
-- "the scraper was broken this week" — the failure mode that silently ruins
-- every job-market chart.
CREATE TABLE IF NOT EXISTS ingest_run (
    id              BIGSERIAL PRIMARY KEY,
    source          TEXT        NOT NULL,
    board_token     TEXT        NOT NULL,
    started_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at     TIMESTAMPTZ,
    status          TEXT        NOT NULL DEFAULT 'running',  -- running|ok|error
    fetched         INTEGER     NOT NULL DEFAULT 0,
    inserted        INTEGER     NOT NULL DEFAULT 0,
    updated         INTEGER     NOT NULL DEFAULT 0,
    unchanged       INTEGER     NOT NULL DEFAULT 0,
    closed          INTEGER     NOT NULL DEFAULT 0,
    error           TEXT
);

CREATE INDEX IF NOT EXISTS ingest_run_board_idx ON ingest_run (source, board_token, started_at DESC);
