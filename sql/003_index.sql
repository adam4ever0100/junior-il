-- junior-il: published index snapshots.
--
-- One row per published measurement. Numbers are stored rather than recomputed
-- on demand so that a figure quoted in October keeps meaning what it meant in
-- October, even after the rules change — `parser_version` says which rules
-- produced it, and `status` says whether the sweep behind it was complete.

CREATE TABLE IF NOT EXISTS index_snapshot (
    id              BIGSERIAL PRIMARY KEY,
    taken_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    parser_version  TEXT        NOT NULL,

    -- 'complete' only when every configured board answered on its last poll.
    -- A partial sweep is still recorded, and still labelled, because hiding it
    -- would leave an unexplained gap in the series.
    status          TEXT        NOT NULL,
    boards_total    INTEGER     NOT NULL,
    boards_ok       INTEGER     NOT NULL,
    boards_retired  INTEGER     NOT NULL DEFAULT 0,

    open_total      INTEGER     NOT NULL,
    open_israel     INTEGER     NOT NULL,
    open_israel_eng INTEGER     NOT NULL,

    -- The headline.
    junior_eligible     INTEGER NOT NULL,
    pct_junior_eligible NUMERIC(5,2),

    -- The supporting breakdown, so the headline can be argued with.
    -- `explicit_entry` counts roles that actually invite 0-1 years, as opposed
    -- to roles that merely never state a requirement. Keeping them apart
    -- matters: "open to a graduate" is a much weaker claim when every one of
    -- them is an omission rather than an invitation.
    explicit_entry  INTEGER     NOT NULL DEFAULT 0,
    bar_3plus       INTEGER     NOT NULL,
    years_unstated  INTEGER     NOT NULL,
    years_vague     INTEGER     NOT NULL,
    junior_titled   INTEGER     NOT NULL,
    degree_required INTEGER     NOT NULL,
    clearance_required INTEGER  NOT NULL,

    notes           TEXT
);

CREATE INDEX IF NOT EXISTS index_snapshot_taken_idx ON index_snapshot (taken_at DESC);

-- Why a posting stopped being open. 'missing_from_board' is the normal case;
-- 'board_retired' means the board itself disappeared, so the posting was never
-- observed closing and must not be counted as open forever.
ALTER TABLE posting ADD COLUMN IF NOT EXISTS closed_reason TEXT;

-- Added after the table first shipped. `CREATE TABLE IF NOT EXISTS` above is a
-- no-op on an existing database, so every later column needs its own
-- idempotent ALTER or the schema silently diverges between a fresh clone and
-- a running one — which is exactly how it was found.
ALTER TABLE index_snapshot ADD COLUMN IF NOT EXISTS explicit_entry INTEGER NOT NULL DEFAULT 0;
