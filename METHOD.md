# Method

How the Junior Hiring Index is produced, in enough detail to reproduce it or
argue with it. If a number on the site disagrees with this document, this
document is the bug.

## The question

**What share of open engineering roles located in Israel can a graduate with no
professional experience apply to without failing a stated requirement?**

Not "how many junior jobs are there" — titles are unreliable. Not "how hard is
it to get hired" — that is unmeasurable from postings. Only what employers
themselves wrote down.

## The sample

Public job-board APIs of companies with their head office or a major R&D centre
in Israel. Today that is 20 Greenhouse boards, listed in
[`ingest/junior_il/boards.py`](ingest/junior_il/boards.py) — in code rather
than a database, because "who counts as an Israeli employer" is a reviewed
decision, not configuration.

Each board is polled with one unauthenticated request. Boards are polled
infrequently, serially, with a delay between them, and with a User-Agent that
names the project and an email address.

**This is a sample, not a census**, and it is weighted toward product
companies — which is the tier the headline finding is about.

## Pipeline

| Stage | Command | What it does |
|---|---|---|
| Ingest | `junior-il ingest` | Boards → `posting`, raw payload stored verbatim |
| Reparse | `junior-il reparse` | Rebuild `description` from stored payloads after a parser fix |
| Retire | `junior-il retire-boards` | Close postings of boards that no longer exist |
| Normalize | `junior-il normalize` | `posting` → `posting_norm` using the rules below |
| Index | `junior-il index --snapshot` | Count, check, record in `index_snapshot` |

## Definitions

### Located in Israel

A posting counts as Israeli if **any** segment of its location field names an
Israeli city or the country. Location strings pack several places into one
field in every possible style — `Tel Aviv/ Netanya, Israel`, `Glilot; Tel
Aviv`, `Israel - Raanana` — so they are split on `;`, `,`, `/` and spaced
dashes, but never on a bare hyphen, which would cut `Tel Aviv-Yafo` in half.

Two consequences, both deliberate:

- A role listed `Tel Aviv; London` counts as Israeli. That is the right answer
  to "can someone living here take this job", and it means a global role
  listing six cities counts as one of them.
- **Searching for the word "Israel" does not work.** In the October corpus,
  206 open roles are in Israel and only 119 of them contain "Israel" anywhere
  in the location field. `Tel Aviv` alone is the single most common value.
  Any analysis of this market built on a country-name filter is missing about
  42% of it.

Canonical city list and aliases:
[`normalize/location.py`](ingest/junior_il/normalize/location.py).

### Engineering

By title, not department. Departments in this corpus are unusable for the
purpose — Israeli R&D postings arrive under `R&D`, `Engineering`,
`CX - R&D Engineering`, `Development`, `Products and AI R&D`,
`Engineering - SSE` and `VM, Public Safety`, while plenty of non-engineering
roles sit under `R&D` too. Department is used only to rescue a title with no
role word in it at all.

Two judgement calls worth disagreeing with:

- **QA, automation, test and SDET roles count as engineering.** They are
  engineering jobs, and they are one of the few routes in this market that
  opens to a graduate at all. Excluding them would understate the open door.
- **Sales Engineer, Solutions Engineer, Solutions Architect and Technical
  Support Engineer do not count.** They are customer-facing roles that happen
  to contain an engineering word. This narrows the denominator; both counts are
  in the database if you want to recompute it the other way.

### Experience

Every stated years-of-experience requirement is extracted with its context.

- **A range states its floor.** `4-8 years` demands four; the eight is the top
  of a band, not a second requirement. Reading the ceiling would brand
  `0-2 years` — an explicitly junior posting — as closed to juniors.
- **The steepest requirement is the bar** (`years_bar`), because every
  requirement in a posting has to be met. `7+ years overall, 1+ years with
  Kafka` is a seven-year job. Published figures use `years_bar`; `years_floor`
  (the gentlest requirement) exists for auditing only, and would understate
  the barrier if it were ever published.
- **"A plus" is scoped.** A preference marker demotes a figure only when it
  governs it. In the real posting `6+ years of backend development experience
  using Java (Go is a plus)`, the "a plus" belongs to Go; treating the whole
  line as preferred deleted a genuine six-year requirement.
- **Silence is not zero.** A posting that never mentions experience is
  `years_stated = false`, reported in its own bucket. It is not a zero-year
  requirement, and it is not evidence of an open door.
- **"Several years" is its own case** (`years_vague`): a requirement with no
  number. It counts as a barrier, because reading it as silence would turn a
  closed door into an open one.
- A graduate is assumed to have **one year** (`GRADUATE_YEARS = 1`), so a
  `1+ years` posting counts as within reach.

### Junior-eligible — the headline

A posting is junior-eligible when **all** of these hold:

1. located in Israel, and
2. engineering by the definition above, and
3. its title does not say senior, staff, principal, lead, architect, manager,
   director, head or VP, and
4. it states no years requirement, or its bar is ≤ 1 year, and
5. it does not demand an unquantified "several years".

**Degree and security clearance are recorded but excluded from this verdict.**
Both are real barriers — 50 of the 123 Israeli engineering roles require a
degree — but folding them in would make the headline rest on reading a
"military service" mention correctly, and the number has to survive someone
arguing with it. They are published as separate figures.

Note the distinction between *eligible* and *invited*: `explicit_entry` counts
roles that actually state a 0-1 year bar. In the October snapshot that is
**zero of 123** — every eligible role qualifies by omission, not invitation.

## Guards against the usual failure modes

A job-market index goes wrong quietly rather than loudly. These are the
specific wrong numbers this pipeline refuses to produce:

- **A failed fetch is not an empty board.** A source raises rather than
  returning a short list, and postings are closed only after a fully
  successful fetch. Otherwise one network timeout fabricates a hiring
  slowdown. This is not hypothetical — the September sweep hit a `ReadTimeout`.
- **A vanished board is not an eternally open job.** A 404 is permanent where a
  timeout is not, so `retire-boards` closes those postings with
  `closed_reason = 'board_retired'`. Cybereason's board disappeared between
  the September and October sweeps, leaving five postings that would otherwise
  have counted as open indefinitely.
- **A partial sweep is never recorded as complete.** A snapshot is labelled
  `complete` only when every configured board either answered or is retired.
  Partial sweeps are still recorded and still labelled, because a hidden gap
  in the series is worse than a labelled one.
- **The index is never computed over a half-normalized corpus.** A posting
  with no normalized row would read as "not in Israel", shrinking the market
  for reasons unrelated to hiring. `junior-il index` refuses to run.
- **Published numbers are frozen.** Each snapshot stores the `parser_version`
  that produced it, so a figure published under one version of the rules stays
  explainable after they change.

Every rule above is a pure function over strings with tests against real
corpus text, including deliberate false-positive cases. `pytest` from the
repo root.

## Known limits

- **Greenhouse only.** Comeet is next; Workday employers, recruitment
  agencies, and roles posted on LinkedIn alone are entirely absent.
- **20 companies.** A sample, and a product-company-weighted one.
- **Postings, not hires.** A posting may be stale, speculative, already filled,
  or a pipeline-building exercise. This measures what employers ask for, not
  what they do.
- **Stated requirements, not real ones.** Plenty of teams interview a strong
  graduate for a role that says three years. The index measures the stated
  barrier, which is what filters an application before a human sees it.
- **No seniority inference from salary or level codes** — neither is published
  on these boards.
- **One snapshot so far.** Nothing here is a trend until there are several.

## Reproducing it

```bash
docker compose up -d
cd ingest && python3.13 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt
.venv/bin/python -m junior_il.cli initdb
.venv/bin/python -m junior_il.cli ingest
.venv/bin/python -m junior_il.cli retire-boards
.venv/bin/python -m junior_il.cli normalize
.venv/bin/python -m junior_il.cli index
```

Your numbers will differ from any published snapshot, because boards change
daily. That is the point of recording snapshots rather than recomputing.

## Parser changelog

| Version | Date | Change |
|---|---|---|
| `2026.10.18-1` | 18 Oct 2026 | First version. Location, engineering, experience, degree and clearance rules as described above. |

## Corrections

Errors in this method are worth more to me than agreement with its
conclusions. Open an issue, or adamabusaad@gmail.com.
