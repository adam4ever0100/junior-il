import httpx
import pytest

from junior_il.sources.greenhouse import GreenhouseSource

BOARD = {
    "jobs": [
        {
            "id": 123,
            "title": "  Backend Engineer  ",
            "company_name": "Acme",
            "location": {"name": "Tel Aviv, Israel"},
            "departments": [{"name": "R&D"}],
            "content": "<p>3+ years of Python</p>",
            "absolute_url": "https://example.com/123",
            "first_published": "2026-09-01T10:00:00.000Z",
            "updated_at": "2026-09-20T10:00:00-04:00",
        }
    ]
}


def _source(handler):
    transport = httpx.MockTransport(handler)
    return GreenhouseSource(client=httpx.Client(transport=transport))


def test_maps_board_payload_to_postings():
    source = _source(lambda request: httpx.Response(200, json=BOARD))
    posting = list(source.fetch("acme"))[0]
    assert posting.external_id == "123"
    assert posting.title == "Backend Engineer"        # whitespace trimmed
    assert posting.location_raw == "Tel Aviv, Israel"
    assert posting.department == "R&D"
    assert posting.description == "3+ years of Python"  # html stripped
    assert posting.posted_at.year == 2026
    assert posting.raw["id"] == 123


def test_missing_company_name_falls_back_to_board_token():
    payload = {"jobs": [{"id": 1, "title": "Dev", "location": {"name": ""}}]}
    source = _source(lambda request: httpx.Response(200, json=payload))
    assert list(source.fetch("someboard"))[0].company == "someboard"


def test_unexpected_payload_raises_rather_than_returning_nothing():
    # Returning [] here would make the caller close every posting on the board.
    source = _source(lambda request: httpx.Response(200, json={"error": "nope"}))
    with pytest.raises(ValueError):
        list(source.fetch("acme"))


def test_retries_transient_failure_then_succeeds():
    calls = {"n": 0}

    def handler(request):
        calls["n"] += 1
        if calls["n"] < 3:
            raise httpx.ReadTimeout("boom", request=request)
        return httpx.Response(200, json=BOARD)

    import junior_il.sources.greenhouse as gh
    gh.BACKOFF_SECONDS = 0  # keep the test fast
    assert len(list(_source(handler).fetch("acme"))) == 1
    assert calls["n"] == 3


def test_does_not_retry_a_404():
    calls = {"n": 0}

    def handler(request):
        calls["n"] += 1
        return httpx.Response(404, json={})

    with pytest.raises(httpx.HTTPStatusError):
        list(_source(handler).fetch("gone"))
    assert calls["n"] == 1
