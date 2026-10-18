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


def flat(html):
    """Collapse whitespace: the template wraps prose across source lines."""
    return " ".join(html.split())


def test_the_headline_is_the_invited_count_not_the_eligible_count():
    html = render()
    assert '<div class="hero-n">0</div>' in html
    assert "not because they invite someone starting out" in flat(html)


def test_the_hero_claim_follows_the_numbers_rather_than_being_written():
    # It asserts *why* roles are open, so it cannot be fixed prose. With one
    # role inviting a graduate, "only because they state no requirement" is a
    # false statement about the data.
    html = flat(render(counts=counts(explicit_entry=1, junior_eligible=4)))
    assert "1 that invites a graduate outright, and 3 that simply state no" in html
    assert "only because" not in html


def test_hero_claim_when_every_eligible_role_is_explicit():
    html = flat(render(counts=counts(explicit_entry=3, junior_eligible=3)))
    assert "each one says so explicitly" in html


def test_hero_claim_when_nothing_is_open_at_all():
    html = flat(render(counts=counts(explicit_entry=0, junior_eligible=0)))
    assert "cannot be applied to" in html or "can be applied to by a graduate at all" in html


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
    assert names == {"index.html", "he.html", "latest.json", "series.json"}
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


# --- Hebrew -------------------------------------------------------------

def test_the_hebrew_page_is_a_proper_rtl_document():
    html = site.render_html(counts=counts(), histogram=[], companies=COMPANIES,
                            eligible=ELIGIBLE, series=SERIES, generated_at=NOW,
                            lang=site.HEBREW)
    assert '<html lang="he" dir="rtl">' in html
    assert "\u05de\u05d3\u05d3" in html          # מדד, in the title
    assert "How open is Israeli tech" not in html


def test_the_two_pages_report_identical_numbers():
    # A translation bug that changed a number would be far worse than an
    # awkward sentence, so the figures are compared directly.
    import re
    pages = {}
    for lang in site.LANGUAGES:
        html = site.render_html(counts=counts(), histogram=[{"bucket": "5+", "roles": 79}],
                                companies=COMPANIES, eligible=ELIGIBLE,
                                series=SERIES, generated_at=NOW, lang=lang)
        pages[lang.code] = {
            "hero": re.search(r'hero-n">(\d+)<', html).group(1),
            "stats": re.findall(r'stat-n">(\d+)<', html),
            "bars": payload(html)["bars"]["values"],
        }
    assert pages["en"]["hero"] == pages["he"]["hero"]
    assert pages["en"]["stats"] == pages["he"]["stats"]
    assert pages["en"]["bars"] == pages["he"]["bars"]


def test_each_page_links_to_the_other():
    en = site.render_html(counts=counts(), histogram=[], companies=COMPANIES,
                          eligible=ELIGIBLE, series=SERIES, generated_at=NOW,
                          lang=site.ENGLISH)
    he = site.render_html(counts=counts(), histogram=[], companies=COMPANIES,
                          eligible=ELIGIBLE, series=SERIES, generated_at=NOW,
                          lang=site.HEBREW)
    assert 'href="he.html"' in en and 'hreflang="he"' in en
    assert 'href="index.html"' in he and 'hreflang="en"' in he


def test_hebrew_hero_claim_also_follows_the_numbers():
    html = flat(site.render_html(counts=counts(explicit_entry=1, junior_eligible=4),
                                 histogram=[], companies=COMPANIES, eligible=ELIGIBLE,
                                 series=SERIES, generated_at=NOW, lang=site.HEBREW))
    # "4 can be applied to in total: 1 ... and 3 ..."
    assert "4" in html and "\u05d4\u05e9\u05de\u05d8\u05d4" in html   # השמטה = omission


def test_the_rtl_page_tells_the_chart_to_flip():
    data = payload(site.render_html(counts=counts(), histogram=[], companies=COMPANIES,
                                    eligible=ELIGIBLE, series=SERIES, generated_at=NOW,
                                    lang=site.HEBREW))
    assert data["bars"]["rtl"] is True
    assert payload(site.render_html(counts=counts(), histogram=[], companies=COMPANIES,
                                    eligible=ELIGIBLE, series=SERIES,
                                    generated_at=NOW))["bars"]["rtl"] is False


def test_every_string_key_exists_in_both_languages():
    # A missing key is a KeyError at publish time, in whichever language was
    # edited second.
    assert set(site.ENGLISH.strings) == set(site.HEBREW.strings)
    assert set(site.ENGLISH.buckets) == set(site.HEBREW.buckets)
    assert set(site.ENGLISH.buckets) == set(site.BUCKET_ORDER)


def test_role_rows_carry_dir_auto_so_latin_titles_survive_rtl():
    html = site.render_html(counts=counts(), histogram=[], companies=COMPANIES,
                            eligible=ELIGIBLE, series=SERIES, generated_at=NOW,
                            lang=site.HEBREW)
    assert '<li dir="auto">' in html


def test_the_hero_caption_stays_a_noun_phrase_in_both_languages():
    """Pins the shape, because grammar cannot be asserted directly.

    The hero number is 0 some weeks and 4 others. Both languages inflect with
    it — English "1 ... state", Hebrew "1 ... \u05de\u05e6\u05d9\u05d9\u05e0\u05d5\u05ea" \u2014 so each caption is a
    noun phrase whose relative clause agrees with "roles", never with the
    count. A future edit that turns it back into a sentence breaks this.
    """
    for lang in site.LANGUAGES:
        caption = lang.strings["hero_caption"]
        assert caption.startswith("\u2014 "), lang.code
        for count in (0, 1, 5, 137):
            assert "{il_eng}" in caption
            caption.format(il_eng=count)      # must not raise
