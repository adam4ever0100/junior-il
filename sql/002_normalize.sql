-- junior-il: normalized view of each posting, derived from `posting`.
--
-- Separate table rather than columns on `posting` for two reasons: the raw
-- ingest stage must stay independent of parser changes, and a re-normalization
-- is then a DELETE + INSERT that can never corrupt collected data.

CREATE TABLE IF NOT EXISTS posting_norm (
    posting_id      BIGINT PRIMARY KEY REFERENCES posting (id) ON DELETE CASCADE,

    -- Which build of the rules produced this row. An index snapshot records the
    -- same value, so a number published in October stays explainable after the
    -- rules change in November.
    parser_version  TEXT        NOT NULL,
    normalized_at   TIMESTAMPTZ NOT NULL DEFAULT now(),

    -- Location
    is_israel       BOOLEAN     NOT NULL,
    il_cities       TEXT[]      NOT NULL DEFAULT '{}',   -- canonical names matched
    is_remote       BOOLEAN     NOT NULL DEFAULT FALSE,

    -- Role shape
    is_engineering  BOOLEAN     NOT NULL,
    seniority       TEXT        NOT NULL,   -- junior|mid|senior|lead|manager|unspecified
    junior_signal   BOOLEAN     NOT NULL,   -- title says junior/graduate/intern/student

    -- Experience barrier. years_stated distinguishes "no experience required"
    -- from "the posting never mentions experience" — conflating those two is
    -- the easiest way to overstate how open a market is.
    years_stated    BOOLEAN     NOT NULL,
    years_vague     BOOLEAN     NOT NULL DEFAULT FALSE,  -- "several years", no number
    years_floor     INTEGER,                -- gentlest stated requirement
    years_bar       INTEGER,                -- steepest: what a candidate must clear
    years_evidence  TEXT,                   -- the phrase it came from, for auditing

    -- Other hard filters
    degree_required     BOOLEAN NOT NULL DEFAULT FALSE,
    clearance_required  BOOLEAN NOT NULL DEFAULT FALSE,

    -- The headline verdict, stored rather than computed at query time so that
    -- a published snapshot cannot silently change meaning later.
    junior_eligible BOOLEAN     NOT NULL
);

CREATE INDEX IF NOT EXISTS posting_norm_israel_idx
    ON posting_norm (is_israel, is_engineering) WHERE is_israel AND is_engineering;
CREATE INDEX IF NOT EXISTS posting_norm_eligible_idx
    ON posting_norm (junior_eligible) WHERE junior_eligible;
CREATE INDEX IF NOT EXISTS posting_norm_version_idx
    ON posting_norm (parser_version);
