# junior-il — two-week plan to a live Junior Hiring Index

Start: Sun 18 Oct 2026 · Launch deadline: **Sat 31 Oct 2026**

## The one goal

A public URL that shows one defensible number: **how much of the Israeli
tech market is actually open to a zero-experience CS graduate**, updated
automatically, with the method published.

Not a job board. Not a bot that applies. Market analytics.

## Hard rules (agreed, do not renegotiate at 1am)

1. **Live by day 9.** Days 10-14 are polish and slack. If day 9 arrives and
   it is not deployed, cut features — never the deploy.
2. **Publish aggregates, not other people's job descriptions.** Raw text stays
   in Postgres; the site shows counts, percentages and links out. This is what
   keeps the project clean legally and reputationally.
3. **A broken poll must never become a market finding.** Compute a snapshot
   only from a sweep where every board returned `ok`. Otherwise mark the
   snapshot `partial` and say so on the page.
4. **No unverifiable claims.** Everything on the page must be reproducible by
   a stranger from `METHOD.md` and the committed data.
5. Java/Spring is **November**, after the URL exists.

---

## Day 0 — today, 1 hour

- [x] `git init` is done; create the **public** GitHub repo `junior-il` and push. → https://github.com/adam4ever0100/junior-il
- [x] Rewrite `README.md` as the project's pitch, not setup notes: what the
      index measures, why nobody else publishes it, how to reproduce it.
- [x] Add `.gitignore` entries for `.venv/`, `__pycache__/`, `.pytest_cache/`
      (they are currently sitting in the tree).
- [x] `docker compose up -d` and confirm the existing ~900 postings survived in
      the `pgdata` volume. If not, re-run `ingest` — it is idempotent.

Done means: a public link exists. Even empty, it is a link.

## Days 1-3 — the normalizer — **DONE 18 Oct**

Shipped as `ingest/junior_il/normalize/` (location, years, titles, clauses,
core) plus `posting_norm`, `junior-il normalize`, and 54 new tests. Four things
turned up that were not in the plan:

- **`html_to_text` was silently broken.** Greenhouse sends HTML-escaped HTML,
  so one stripping pass produced literal "<li>" text and destroyed the line
  structure every years regex depends on. All 921 descriptions were affected.
  Fixed with a bounded second pass, and `junior-il reparse` rebuilt every
  description **from the stored raw payload, with no re-fetch** — which is the
  concrete payoff of keeping `raw`.
- **`years_min`/`years_max` were the wrong names.** What matters is the
  steepest requirement, because all of them must be met: "7+ years overall,
  1+ years with Kafka" is a seven-year job. Renamed to `years_floor` (gentlest,
  kept for auditing) and `years_bar` (what a candidate must clear). Published
  figures use `years_bar`.
- **"Several years of hands-on experience"** needed its own field
  (`years_vague`). It was falling into "unstated", which the eligibility rule
  reads as "no experience required" — a closed door counted as open.
- **Three bugs the tests caught**, all biasing toward a market that looks more
  open than it is: `100 years` matched as `00 years` (threshold 0); a
  parenthetical "(Go is a plus)" demoted an unrelated "6+ years" requirement;
  and a bare "or equivalent" waived every degree clause.

### Original scope, for reference

New package `ingest/junior_il/normalize/`, pure functions, no DB access, each
with tests. New table `posting_norm` keyed to `posting.id`, plus
`parser_version TEXT` so a future parser change cannot silently rewrite history.

Fields to derive per posting:

| field | how |
|---|---|
| `is_israel` | canonicalize `location_raw`: Tel Aviv / TLV / תל אביב / Herzliya / Ra'anana / Yokneam / Beer Sheva / Haifa / "Israel" / "Hybrid - IL". Keep a reviewed alias table **in code**, like `boards.py`. |
| `is_engineering` | title + department. Exclude sales, marketing, HR, finance, legal, support — the NICE "Employer Branding Student" trap. |
| `min_years` | regex over description: `3+ years`, `at least 5 years`, `2-4 years`, `3-5 שנות ניסיון`, `ניסיון של 3 שנים`. Take the **minimum** stated. NULL when nothing is stated. |
| `junior_signal` | title matches junior / graduate / grad / student / intern / entry.level / new.grad / ג'וניור / סטודנט / מתמחה. |
| `degree_clause` | B.Sc / BA / תואר required. |
| `clearance_clause` | security clearance / סיווג / defence-sector language. |
| `seniority` | senior / staff / principal / lead / manager / architect in title → excluded from the junior-eligible pool regardless of years. |

Rules worth getting right, because these are the ones a critic will attack:
- `min_years` NULL is **not** zero. Report it as its own bucket, "unstated".
- A role is **junior-eligible** when: open AND israel AND engineering AND not
  senior-titled AND (`junior_signal` OR `min_years <= 1`).
- Every regex gets a test with a real string from the corpus, including a
  Hebrew one and at least one deliberate false-positive case
  ("5 years of experience building X is a plus").

Done means: `pytest` green, and `junior-il normalize` fills `posting_norm` for
all ~900 rows in one pass.

## Day 4 — the index itself

New table `index_snapshot`: `taken_at`, `parser_version`, `boards_ok`,
`boards_total`, `status` (`complete`/`partial`), `open_il_eng`,
`junior_eligible`, `pct_junior_eligible`, `demand_3plus`, `unstated_years`.

New command `junior-il index --snapshot` → computes, prints, persists.

Write `METHOD.md` in the same sitting, while the definitions are fresh: the
exact SQL, the exclusion rules, the sample (which boards, why those), and the
known limitations — Greenhouse/Comeet only, no Workday, no agencies, no roles
posted on LinkedIn alone. **Stating the limits is what makes it quotable
rather than dismissible.**

Headline sentence the page must be able to generate:

> Of **N** open engineering roles located in Israel across **M** company
> boards, **K** are open to a candidate with no professional experience.

Done means: your 23 Sep finding (192 / 1 / 135) reproduces from code, not notes.

## Days 5-6 — Comeet source (credibility through coverage)

20 Greenhouse boards is a thin, self-selected sample and that is the first
thing anyone will say. Comeet is Israeli and widely used here, so it roughly
doubles Israeli coverage, and your `Source` ABC already exists — this is a
contained addition, not a refactor.

- [ ] `sources/comeet.py` implementing the same interface, with the same
      contract: `fetch()` **raises** rather than returning a short list.
- [ ] 15-25 Israeli Comeet boards, each verified HTTP 200 and non-empty, added
      to `boards.py` with the same reviewed-decision comment.
- [ ] Tests from saved fixtures, no network.
- [ ] Polite client: identifying User-Agent (`junior-il/0.1 (+<repo url>)`),
      serial requests, small delay. You are a guest on these APIs.

If day 6 ends and Comeet is not working: **stop, ship with Greenhouse, say so
in METHOD.md.** Coverage can grow after launch.

## Days 7-8 — the static site

`junior-il publish --out site/` generates:
- `site/index.html` — one headline number, big; one bar chart (roles by
  minimum-years bucket: 0-1 / 2 / 3-4 / 5+ / unstated); one table of companies
  with open-Israel-engineering counts and junior-eligible counts; a line chart
  of the snapshot series (it will have one point at launch — that is fine, it
  is the reason to come back next month).
- `site/data/latest.json` and `site/data/series.json` — committed, so the data
  is downloadable and the history is in git.
- Footer: method link, last-updated timestamp, board count, your name, email,
  LinkedIn. **The point of the whole project is that your name is on the
  number** — do not be shy here.

Chart.js from a CDN, no build step, no framework. Jinja2 or an f-string
template; do not install a static-site generator.

Done means: `open site/index.html` looks like something a journalist would
screenshot.

## Day 9 — LIVE

- [ ] `.github/workflows/ingest.yml`: scheduled weekly (Mondays 06:00 UTC) +
      `workflow_dispatch`. Postgres 17 service container, `initdb`, `ingest`,
      `normalize`, `index --snapshot`, `publish`, then commit `site/` back to
      the repo.
- [ ] `.github/workflows/ci.yml`: pytest on every push. This is the GitHub
      Actions line on your CV, earned.
- [ ] GitHub Pages from `/site` on `main`. Custom domain only if it takes
      under 20 minutes.
- [ ] Run the workflow manually once and watch the page change.

Done means: **a stranger can open the URL.** This is the day the project stops
being a repo and starts being an asset.

## Days 10-11 — polish, in this priority order

1. Hebrew/English toggle (one static page, two text blocks, `lang` attribute
   and `dir="rtl"` — not an i18n library).
2. Mobile layout. Recruiters open links on phones.
3. Per-company table sortable.
4. An `/about` paragraph: who you are, that you are a June 2026 SCE CS grad
   who built this because the market data did not exist. The personal line is
   the reason people share it.

## Day 12 — the launch post

Draft the LinkedIn post (Hebrew + English). Structure: the number first, the
method second, the link third, no complaining about the job market, no "I am
looking for opportunities" in the post body — that reframes it from research
to a plea. Let the work carry it.

## Day 13 — publish and distribute

- [ ] Post it.
- [ ] Send the link to the quiet threads as a **reason to re-contact, not a
      follow-up beg**: Lior Einy (Elad), Hosni Abomokh (Salesforce),
      Muhammad Awawdi (AWS). "I built the dataset I mentioned — here it is."
- [ ] Send it to the organisations whose coordinators talk to company HR daily:
      Tsofen, Kav Mashve, Siraj (Walaa Ibrahim), the Riyan centre in Hura.
      They have doors with no bot on them.
- [ ] Offer it to Geektime / a Calcalist tech reporter as a data story. Worst
      case: nothing. Best case: your name next to a number in the press.

## Day 14 — buffer

It will be needed. Something will break on day 9.

---

## After launch (not in the two weeks)

- **November:** Java 21 + Spring Boot read-API over `posting_norm` — the honest
  Java bullet for Amdocs / NICE / Matrix / Check Point.
- The rejection-reason checker, reusing `min_years` / `degree_clause` /
  `clearance_clause`: paste a posting, see which hard filters you fail.
- Second snapshot, early December: the first time the index has a *trend*, it
  becomes news rather than a one-off.
