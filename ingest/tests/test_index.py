"""Index assembly: the completeness rules and the published sentence."""
import pytest

from junior_il.index import COMPLETE, PARTIAL, BoardHealth, headline, render


def counts(**kw):
    base = dict(
        parser_version="test-1", status=COMPLETE, boards_total=20, boards_ok=19,
        boards_retired=1, open_total=916, open_israel=206, open_israel_eng=123,
        junior_eligible=3, pct_junior_eligible=2.44, explicit_entry=0,
        bar_3plus=111, years_unstated=9, years_vague=1, junior_titled=1,
        degree_required=50, clearance_required=0, notes=None,
    )
    base.update(kw)
    return base


def test_a_retired_board_still_counts_as_a_complete_sweep():
    # Its postings have been closed, so the corpus is accounted for — unlike a
    # board that simply failed to answer.
    health = BoardHealth(total=20, ok=19, retired=1, failing=[])
    assert health.status == COMPLETE


def test_a_board_that_did_not_answer_makes_the_sweep_partial():
    health = BoardHealth(total=20, ok=19, retired=0, failing=["greenhouse/nice"])
    assert health.status == PARTIAL


def test_a_sweep_with_nothing_recorded_is_partial():
    assert BoardHealth(total=20, ok=0, retired=0, failing=[]).status == PARTIAL


def test_headline_names_the_denominator_and_the_sample_size():
    text = headline(counts())
    assert "123 open engineering roles located in Israel" in text
    assert "20 company boards" in text
    assert "3 are open to a candidate with no professional experience" in text


def test_render_separates_eligible_from_invited():
    # The weaker claim has to be visible: every eligible role in the October
    # corpus qualifies by omission, not by inviting a beginner.
    text = render(counts(), [{"bucket": "5+", "roles": 74}])
    assert "junior-eligible" in text and "of which invited" in text


def test_render_reports_the_sweep_status_and_parser_version():
    text = render(counts(), [])
    assert "sweep: complete" in text
    assert "parser: test-1" in text


def test_render_surfaces_boards_that_did_not_answer():
    text = render(counts(status=PARTIAL, notes="boards not answering: greenhouse/nice"), [])
    assert "sweep: partial" in text
    assert "greenhouse/nice" in text


def test_percentage_is_omitted_rather_than_faked_when_there_is_no_denominator():
    text = render(counts(open_israel_eng=0, junior_eligible=0,
                         pct_junior_eligible=None), [])
    assert "%" not in text.split("experience bar")[0].split("junior-eligible")[1][:40]


@pytest.mark.parametrize("bucket", ["0-1", "2", "3-4", "5+", "unquantified", "unstated"])
def test_every_histogram_bucket_renders(bucket):
    text = render(counts(), [{"bucket": bucket, "roles": 7}])
    assert bucket in text
