"""The published page. It must not invent, drop, or mangle anything."""
import json
from datetime import datetime, timezone

from junior_il import site

NOW = datetime(2026, 10, 18, 19, 30, tzinfo=timezone.utc)


def counts(**kw):
    base = dict(
        parser_version="test-1", status="complete", boards_total=21, boards_ok=21,
        boards_retired=0, open_total=926, open_israel=213, open_israel_eng=129,
        junior_eligible=3, pct_junior_eligible=2.33, explicit_entry=0,
        bar_3plus=117, years_unstated=9, years_vague=1, junior_titled=1,
        degree_required=51, clearance_required=0, notes=None,
    )
    base.update(kw)
    return base


COMPANIES = [{"company": "Cato Networks", "il_eng": 27, "eligible": 2,
              "bar_3plus": 23, "bar_5plus": 14}]
ELIGIBLE = [{"company": "Cato Networks", "title": "SW Engineer",
             "location_raw": "Tel Aviv District, Israel",
             "url": "https://example.com/job/1", "source": "greenhouse"}]
SERIES = [{"taken_at": NOW, "status": "complete", "open_israel_eng": 129,
           "junior_eligible": 3, "pct_junior_eligible": 2.33,
           "parser_version": "test-1"}]


def render(**kw):
    args = dict(counts=counts(), histogram=[{"bucket": "5+", "roles": 79}],
                companies=COMPANIES, eligible=ELIGIBLE, series=SERIES,
                generated_at=NOW)
    args.update(kw)
    return site.render_html(**args)


def payload(html):
    start = html.index('id="payload" type="application/json">') + len(
        'id="payload" type="application/json">')
    return json.loads(html[start:html.index("</script>", start)].replace("<\\/", "</"))


def test_empty_buckets_are_still_drawn():
    # A GROUP BY omits a bucket with no rows. Dropping it from the chart
    # deletes the "0-1 years" column — the one fact the page exists to show.
    data = payload(render())["bars"]
    assert data["labels"][0] == "0–1 years"
    assert data["values"][0] == 0
    assert len(data["values"]) == 6


def test_the_headline_is_the_invited_count_not_the_eligible_count():
    html = render()
    assert '<div class="hero-n">0</div>' in html
    # Collapse whitespace: the template wraps prose across source lines.
    assert "not because they invite someone starting out" in " ".join(html.split())


def test_company_names_are_escaped():
    html = render(companies=[{"company": 'A&B <script>alert(1)</script>',
                              "il_eng": 1, "eligible": 0, "bar_3plus": 1,
                              "bar_5plus": 0}])
    assert "<script>alert(1)</script>" not in html
    assert "A&amp;B" in html


def test_role_links_are_escaped_and_rel_protected():
    html = render(eligible=[{"company": "X", "title": 'T" onmouseover="x',
                             "location_raw": "Tel Aviv",
                             "url": 'https://e.com/?a=1&b=2', "source": "greenhouse"}])
    assert 'onmouseover="x' not in html
    assert 'rel="nofollow noopener"' in html
    assert "a=1&amp;b=2" in html


def test_no_eligible_roles_says_so_plainly():
    html = render(eligible=[])
    assert "Not one open engineering role" in html
    assert "<ul class=\"roles\">" not in html


def test_a_single_snapshot_is_not_plotted_as_a_trend():
    html = render(series=SERIES)
    assert 'id="trend"' not in html
    assert "first snapshot" in html


def test_several_snapshots_are_plotted_oldest_first():
    older = dict(SERIES[0], taken_at=datetime(2026, 9, 23, tzinfo=timezone.utc),
                 pct_junior_eligible=1.1)
    html = render(series=[SERIES[0], older])   # db returns newest first
    assert 'id="trend"' in html
    dates = [point["date"] for point in payload(html)["trend"]]
    assert dates == ["2026-09-23", "2026-10-18"]


def test_json_embedded_in_a_script_tag_cannot_close_it():
    assert "</script>" not in site._json_for_script({"x": "</script><b>"})


def test_the_method_and_limits_are_linked_not_implied():
    html = render()
    assert "METHOD.md" in html
    assert "Workday employers, agencies" in html


def test_sweep_status_and_parser_version_are_on_the_page():
    html = render(counts=counts(status="partial", boards_ok=19, boards_retired=1))
    assert "partial" in html and "19/21" in html and "test-1" in html


def test_build_writes_the_page_and_its_data(tmp_path):
    written = site.build(tmp_path, counts=counts(),
                         histogram=[{"bucket": "5+", "roles": 79}],
                         companies=COMPANIES, eligible=ELIGIBLE, series=SERIES,
                         generated_at=NOW)
    names = {path.name for path in written}
    assert names == {"index.html", "latest.json", "series.json"}
    latest = json.loads((tmp_path / "data" / "latest.json").read_text())
    assert latest["index"]["junior_eligible"] == 3
    assert latest["experience_bar"] == {"5+": 79}
    assert latest["companies"][0]["company"] == "Cato Networks"


def test_published_data_carries_no_job_description_text(tmp_path):
    # The site publishes counts and links, never the employer's own copy.
    site.build(tmp_path, counts=counts(), histogram=[], companies=COMPANIES,
               eligible=ELIGIBLE, series=SERIES, generated_at=NOW)
    latest = json.loads((tmp_path / "data" / "latest.json").read_text())
    for role in latest["junior_eligible_roles"]:
        assert set(role) == {"company", "title", "location_raw", "url", "source"}
