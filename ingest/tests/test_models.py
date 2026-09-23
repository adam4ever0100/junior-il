from junior_il.models import Posting


def _posting(**kw):
    base = dict(source="greenhouse", board_token="acme", external_id="1",
                company="Acme", title="Backend Engineer")
    base.update(kw)
    return Posting(**base)


def test_hash_is_stable_across_identical_postings():
    assert _posting().content_hash() == _posting().content_hash()


def test_hash_changes_when_content_changes():
    assert _posting().content_hash() != _posting(title="Senior Backend").content_hash()


def test_hash_ignores_fields_that_move_on_every_poll():
    # raw carries ATS bookkeeping that churns without the posting changing.
    assert _posting(raw={"x": 1}).content_hash() == _posting(raw={"x": 2}).content_hash()


def test_field_boundaries_are_not_ambiguous():
    # "ab" + "" must not hash the same as "a" + "b".
    a = _posting(title="ab", location_raw="")
    b = _posting(title="a", location_raw="b")
    assert a.content_hash() != b.content_hash()
