"""Generate the published page.

One static HTML file plus the JSON behind it, written to `site/`. No build
step, no framework, no server: a scheduled job regenerates the files and
commits them, which also means the data's history lives in git where anyone
can audit how a number changed.

Nothing here decides anything. Every figure arrives already computed from
`index.py`, so the page cannot disagree with `junior-il index`.
"""
import json
from datetime import datetime, timezone
from html import escape
from pathlib import Path
from typing import Any, Optional

REPO = "https://github.com/adam4ever0100/junior-il"
CONTACT = "adamabusaad@gmail.com"

# Pinned exactly, from cdnjs. A floating version would let the page break
# without anything in this repository changing.
CHART_JS = "https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js"

BUCKET_ORDER = ("0-1", "2", "3-4", "5+", "unquantified", "unstated")
BUCKET_LABELS = {
    "0-1": "0–1 years",
    "2": "2 years",
    "3-4": "3–4 years",
    "5+": "5+ years",
    "unquantified": "“several years”",
    "unstated": "not stated",
}


def _json_for_script(payload: Any) -> str:
    """JSON safe to inline in a <script> tag."""
    return json.dumps(payload, default=str).replace("</", "<\\/")


def _stat(value: Any, label: str) -> str:
    return (f'<div class="stat"><div class="stat-n">{escape(str(value))}</div>'
            f'<div class="stat-l">{label}</div></div>')


def _company_rows(companies: list[dict]) -> str:
    rows = []
    for row in companies:
        rows.append(
            "<tr>"
            f'<td>{escape(row["company"])}</td>'
            f'<td class="n">{row["il_eng"]}</td>'
            f'<td class="n">{row["bar_3plus"]}</td>'
            f'<td class="n">{row["bar_5plus"]}</td>'
            f'<td class="n{" zero" if not row["eligible"] else ""}">{row["eligible"]}</td>'
            "</tr>"
        )
    return "\n".join(rows)


def _eligible_list(roles: list[dict]) -> str:
    if not roles:
        return ('<p class="none">Not one open engineering role in the sample is '
                "open to a graduate with no professional experience.</p>")
    items = []
    for role in roles:
        label = f'{escape(role["title"])} — {escape(role["company"])}'
        location = escape(role["location_raw"] or "")
        url = role["url"] or ""
        link = (f'<a href="{escape(url, quote=True)}" rel="nofollow noopener" '
                f'target="_blank">{label}</a>') if url else label
        items.append(f"<li>{link} <span class=\"loc\">{location}</span></li>")
    return f'<ul class="roles">{"".join(items)}</ul>'


def render_html(
    counts: dict,
    histogram: list[dict],
    companies: list[dict],
    eligible: list[dict],
    series: list[dict],
    generated_at: datetime,
) -> str:
    buckets = {row["bucket"]: row["roles"] for row in histogram}
    # Every bucket is drawn, including the empty ones. A GROUP BY omits a
    # bucket with no rows, which silently deleted the "0-1 years" bar — the
    # one fact the whole page is about. An absence has to be visible as a
    # flat zero, not as a missing column nobody notices.
    chart_data = {
        "labels": [BUCKET_LABELS[b] for b in BUCKET_ORDER],
        "values": [buckets.get(b, 0) for b in BUCKET_ORDER],
    }
    # Oldest first, so the line reads left to right.
    trend = [
        {"date": row["taken_at"].strftime("%Y-%m-%d"),
         "pct": float(row["pct_junior_eligible"] or 0),
         "eligible": row["junior_eligible"],
         "total": row["open_israel_eng"]}
        for row in reversed(series)
    ]

    il_eng = counts["open_israel_eng"]
    invited = counts["explicit_entry"]
    eligible_n = counts["junior_eligible"]
    silent = eligible_n - invited

    # The sub-heading is generated, not written, because it makes a claim about
    # *why* those roles are open. An earlier version hardcoded "only because
    # they state no requirement at all" — true when nothing invited a graduate,
    # and false the moment one did. Prose that asserts a number has to be
    # derived from that number.
    if eligible_n == 0:
        hero_sub = ("No open engineering role in the sample can be applied to "
                    "by a graduate at all.")
    elif invited == 0:
        hero_sub = (f"{eligible_n} can be applied to in total — but only because "
                    "they state no experience requirement at all, not because "
                    "they invite someone starting out. The door is not ajar; it "
                    "is unlabelled.")
    elif silent == 0:
        hero_sub = (f"{eligible_n} can be applied to in total, and each one says "
                    "so explicitly.")
    else:
        hero_sub = (f"{eligible_n} can be applied to in total: {invited} that "
                    f"invites a graduate outright, and {silent} that simply "
                    "state no requirement at all. Most of the open door is an "
                    "omission rather than an invitation.")

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Junior Hiring Index — Israel</title>
<meta name="description" content="How much of the Israeli tech market is open to a
 computer science graduate with no professional experience. Measured from companies'
 own public job boards, with the method published.">
<script src="{CHART_JS}" defer></script>
<style>
:root {{
  --bg:#fbfaf8; --fg:#1b1a18; --muted:#6b6862; --rule:#e3dfd8;
  --accent:#b4332b; --card:#fff;
}}
@media (prefers-color-scheme: dark) {{
  :root {{ --bg:#17161a; --fg:#ece9e4; --muted:#a39e96; --rule:#322f36;
           --accent:#ff7a6b; --card:#1f1e23; }}
}}
* {{ box-sizing:border-box; }}
body {{
  margin:0; background:var(--bg); color:var(--fg);
  font:16px/1.6 -apple-system,BlinkMacSystemFont,"Segoe UI",Helvetica,Arial,sans-serif;
  -webkit-text-size-adjust:100%;
}}
.wrap {{ max-width:860px; margin:0 auto; padding:48px 16px 72px; }}
h1 {{ font-size:1.55rem; line-height:1.25; margin:0 0 .4em; letter-spacing:-.01em; }}
h2 {{ font-size:1.05rem; margin:2.6em 0 .7em; letter-spacing:.02em;
      text-transform:uppercase; color:var(--muted); font-weight:600; }}
p {{ margin:0 0 1em; max-width:62ch; }}
a {{ color:var(--accent); }}
.lede {{ color:var(--muted); }}
.hero {{ border:1px solid var(--rule); background:var(--card); border-radius:10px;
        padding:28px 24px; margin:28px 0; }}
.hero-n {{ font-size:clamp(3.6rem,17vw,6rem); line-height:.9; font-weight:700;
          letter-spacing:-.04em; color:var(--accent); }}
.hero-c {{ font-size:1.08rem; margin:.5em 0 0; max-width:48ch; }}
.hero-sub {{ margin:1.1em 0 0; padding-top:1.1em; border-top:1px solid var(--rule);
            color:var(--muted); font-size:.95rem; max-width:52ch; }}
.stats {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(130px,1fr));
         gap:1px; background:var(--rule); border:1px solid var(--rule);
         border-radius:10px; overflow:hidden; }}
.stat {{ background:var(--card); padding:16px 18px; }}
.stat-n {{ font-size:1.65rem; font-weight:650; letter-spacing:-.02em; }}
.stat-l {{ color:var(--muted); font-size:.82rem; line-height:1.4; }}
figure {{ margin:0; }}
.chart {{ position:relative; height:300px; }}
table {{ width:100%; border-collapse:collapse; font-size:.92rem; }}
.scroll {{ overflow-x:auto; -webkit-overflow-scrolling:touch; }}
th,td {{ text-align:left; padding:9px 12px; border-bottom:1px solid var(--rule);
        white-space:nowrap; }}
th {{ color:var(--muted); font-weight:600; font-size:.78rem;
      text-transform:uppercase; letter-spacing:.04em; }}
td.n {{ text-align:right; font-variant-numeric:tabular-nums; }}
td.zero {{ color:var(--muted); }}
.roles {{ list-style:none; padding:0; margin:0; }}
.roles li {{ padding:11px 0; border-bottom:1px solid var(--rule); }}
.loc {{ color:var(--muted); font-size:.85rem; display:block; }}
.none {{ font-size:1.05rem; }}
footer {{ margin-top:56px; padding-top:24px; border-top:1px solid var(--rule);
         color:var(--muted); font-size:.85rem; }}
footer p {{ max-width:70ch; }}
code {{ font-size:.85em; }}
</style>
</head>
<body>
<div class="wrap">

<h1>How open is Israeli tech to a graduate with no experience?</h1>
<p class="lede">Measured from {counts['boards_total']} companies' own public job
boards, not from opinion. Updated automatically; the method is published.</p>

<div class="hero">
  <div class="hero-n">{invited}</div>
  <p class="hero-c">of <strong>{il_eng}</strong> open engineering roles located in
  Israel state an experience requirement a graduate could meet.</p>
  <p class="hero-sub">{hero_sub}</p>
</div>

<div class="stats">
  {_stat(counts['open_israel'], 'open roles located in Israel')}
  {_stat(il_eng, 'of those, engineering')}
  {_stat(counts['bar_3plus'], 'demand 3+ years')}
  {_stat(counts['degree_required'], 'require a degree')}
  {_stat(counts['junior_titled'], 'junior-titled, any field')}
</div>

<h2>The experience bar</h2>
<p>Every stated requirement, read as the steepest figure a candidate must clear.
A range states its floor: “4–8 years” counts as four. Postings that never
mention experience are kept separate from postings that ask for none.</p>
<figure><div class="chart"><canvas id="bars"></canvas></div></figure>

<h2>Where a graduate can apply</h2>
{_eligible_list(eligible)}

<h2>By company</h2>
<div class="scroll"><table>
<thead><tr><th>Company</th><th class="n">IL eng.</th><th class="n">3+ yrs</th>
<th class="n">5+ yrs</th><th class="n">Open to a grad</th></tr></thead>
<tbody>
{_company_rows(companies)}
</tbody></table></div>

<h2>Over time</h2>
{'<figure><div class="chart"><canvas id="trend"></canvas></div></figure>'
 if len(trend) > 1 else
 '<p>This is the first snapshot. A single measurement is not a trend, so there '
 'is nothing to plot yet — come back next month.</p>'}

<footer>
<p><strong>Method.</strong> What counts as Israel, as engineering, and as an
experience requirement is written down in
<a href="{REPO}/blob/main/METHOD.md">METHOD.md</a>, together with the limits of
the sample: {counts['boards_total']} company boards on Greenhouse and Comeet
only, so Workday employers, agencies and roles posted on LinkedIn alone are
absent. Corrections are worth more to me than agreement —
<a href="{REPO}/issues">open an issue</a>.</p>
<p>Sweep <strong>{escape(counts['status'])}</strong>
({counts['boards_ok']}/{counts['boards_total']} boards answered,
{counts['boards_retired']} retired) · parser
<code>{escape(counts['parser_version'])}</code> · generated
{generated_at:%Y-%m-%d %H:%M} UTC ·
<a href="data/latest.json">latest.json</a> ·
<a href="{REPO}">source</a></p>
<p>Built by Adam Abu Saad — B.Sc. Computer Science, Shamoon College of
Engineering, graduating June 2026. I started measuring this market because I am
in it, and the data I wanted did not exist.
<a href="mailto:{CONTACT}">{CONTACT}</a></p>
</footer>
</div>

<script id="payload" type="application/json">{_json_for_script(
    {"bars": chart_data, "trend": trend})}</script>
<script>
window.addEventListener('load', function () {{
  if (typeof Chart === 'undefined') return;
  var data = JSON.parse(document.getElementById('payload').textContent);
  var css = getComputedStyle(document.documentElement);
  var accent = css.getPropertyValue('--accent').trim();
  var muted = css.getPropertyValue('--muted').trim();
  var rule = css.getPropertyValue('--rule').trim();
  Chart.defaults.color = muted;
  Chart.defaults.font.family = getComputedStyle(document.body).fontFamily;

  new Chart(document.getElementById('bars'), {{
    type: 'bar',
    data: {{ labels: data.bars.labels,
             datasets: [{{ data: data.bars.values, backgroundColor: accent,
                          borderRadius: 3 }}] }},
    options: {{ responsive: true, maintainAspectRatio: false,
      plugins: {{ legend: {{ display: false }},
        tooltip: {{ callbacks: {{ label: function (c) {{
          return c.parsed.y + ' roles'; }} }} }} }},
      scales: {{ x: {{ grid: {{ display: false }} }},
                 y: {{ beginAtZero: true, grid: {{ color: rule }},
                       ticks: {{ precision: 0 }} }} }} }}
  }});

  var trendCanvas = document.getElementById('trend');
  if (trendCanvas && data.trend.length > 1) {{
    new Chart(trendCanvas, {{
      type: 'line',
      data: {{ labels: data.trend.map(function (p) {{ return p.date; }}),
               datasets: [{{ data: data.trend.map(function (p) {{ return p.pct; }}),
                            borderColor: accent, backgroundColor: accent,
                            tension: .2, pointRadius: 3 }}] }},
      options: {{ responsive: true, maintainAspectRatio: false,
        plugins: {{ legend: {{ display: false }},
          tooltip: {{ callbacks: {{ label: function (c) {{
            var p = data.trend[c.dataIndex];
            return p.eligible + ' of ' + p.total + ' (' + p.pct + '%)'; }} }} }} }},
        scales: {{ x: {{ grid: {{ display: false }} }},
                   y: {{ beginAtZero: true, grid: {{ color: rule }},
                         ticks: {{ callback: function (v) {{ return v + '%'; }} }} }} }} }}
    }});
  }}
}});
</script>
</body>
</html>
"""


def build(
    out_dir: Path,
    counts: dict,
    histogram: list[dict],
    companies: list[dict],
    eligible: list[dict],
    series: list[dict],
    generated_at: Optional[datetime] = None,
) -> list[Path]:
    generated_at = generated_at or datetime.now(timezone.utc)
    out_dir = Path(out_dir)
    (out_dir / "data").mkdir(parents=True, exist_ok=True)

    latest = {
        "generated_at": generated_at.isoformat(),
        "index": counts,
        "experience_bar": {row["bucket"]: row["roles"] for row in histogram},
        "companies": [dict(row) for row in companies],
        "junior_eligible_roles": [dict(row) for row in eligible],
        "method": f"{REPO}/blob/main/METHOD.md",
    }
    written = []
    for name, payload in (
        ("data/latest.json", latest),
        ("data/series.json", [dict(row) for row in series]),
    ):
        path = out_dir / name
        path.write_text(json.dumps(payload, indent=2, default=str) + "\n",
                        encoding="utf-8")
        written.append(path)

    page = out_dir / "index.html"
    page.write_text(
        render_html(counts, histogram, companies, eligible, series, generated_at),
        encoding="utf-8",
    )
    written.append(page)
    return written
