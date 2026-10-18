"""Comeet source. Payload shape copied from the live API, text written here."""
import httpx
import pytest

from junior_il.sources.comeet import ComeetSource

JOB = {
    "uid": "FF.049",
    "name": "  Backend Engineer  ",
    "company_name": "Acme",
    "department": "Engineering",
    "location": {"name": "Tel Aviv, Israel", "country": "IL",
                 "city": "Tel Aviv-Yafo", "state": "Tel Aviv District"},
    "employment_type": "Full-time",
    "workplace_type": "Hybrid",
    "time_updated": "2026-10-18T18:52:55Z",
    "is_internal": False,
    "url_comeet_hosted_page": "https://www.comeet.com/jobs/acme/A8.00D/backend/FF.049",
    "position_url": "https://www.comeet.co/careers-api/2.0/company/A8.00D/"
                    "positions/FF.049?token=SECRET123",
    "details": [
        {"name": "Requirements", "value": "<ul><li>4+ years of Go</li></ul>", "order": 2},
        {"name": "Description", "value": "<p>Join the platform team.</p>", "order": 1},
    ],
}

BOARDS = {"acme": ("A8.00D", "TOKEN")}


def _source(handler, monkeypatch=None):
    transport = httpx.MockTransport(handler)
    return ComeetSource(client=httpx.Client(transport=transport))


@pytest.fixture(autouse=True)
def _known_board(monkeypatch):
    monkeypatch.setattr("junior_il.sources.comeet.COMEET_BOARDS", BOARDS)


def test_maps_payload_to_postings():
    source = _source(lambda request: httpx.Response(200, json=[JOB]))
    posting = list(source.fetch("acme"))[0]
    assert posting.external_id == "FF.049"
    assert posting.title == "Backend Engineer"
    assert posting.company == "Acme"
    assert posting.location_raw == "Tel Aviv, Israel"
    assert posting.department == "Engineering"
    assert posting.ats_updated_at.year == 2026


def test_sections_are_ordered_and_separated():
    # Out of order in the payload; "Description" must come first, and the
    # requirement must start its own line or the experience rules miss it.
    source = _source(lambda request: httpx.Response(200, json=[JOB]))
    description = list(source.fetch("acme"))[0].description
    assert description.index("Join the platform team") < description.index("4+ years of Go")
    assert "\n4+ years of Go" in description


def test_the_stored_url_is_the_public_page_not_the_tokenised_api_url():
    # position_url carries the API token, and a stored url can end up in
    # published output.
    source = _source(lambda request: httpx.Response(200, json=[JOB]))
    posting = list(source.fetch("acme"))[0]
    assert posting.url.startswith("https://www.comeet.com/jobs/")
    assert "token" not in posting.url and "SECRET123" not in posting.url


def test_posted_at_is_empty_rather_than_guessed():
    # Comeet publishes no creation time, only the last update.
    source = _source(lambda request: httpx.Response(200, json=[JOB]))
    assert list(source.fetch("acme"))[0].posted_at is None


def test_internal_postings_are_skipped():
    internal = dict(JOB, uid="XX.001", is_internal=True)
    source = _source(lambda request: httpx.Response(200, json=[internal, JOB]))
    postings = list(source.fetch("acme"))
    assert [p.external_id for p in postings] == ["FF.049"]


def test_location_falls_back_to_the_structured_parts():
    job = dict(JOB, location={"name": "", "city": "Herzliya", "country": "IL"})
    source = _source(lambda request: httpx.Response(200, json=[job]))
    assert list(source.fetch("acme"))[0].location_raw == "Herzliya, IL"


def test_unknown_board_raises_instead_of_fetching():
    source = _source(lambda request: httpx.Response(200, json=[]))
    with pytest.raises(ValueError, match="no uid/token"):
        list(source.fetch("not-configured"))


def test_unexpected_payload_raises_rather_than_returning_nothing():
    # Returning [] would make the caller close every posting on the board.
    source = _source(lambda request: httpx.Response(200, json={"status": 400}))
    with pytest.raises(ValueError):
        list(source.fetch("acme"))


def test_the_token_is_sent_as_a_query_parameter():
    seen = {}

    def handler(request):
        seen["url"] = str(request.url)
        return httpx.Response(200, json=[JOB])

    list(_source(handler).fetch("acme"))
    assert "token=TOKEN" in seen["url"] and "details=true" in seen["url"]
    assert "/company/A8.00D/positions" in seen["url"]


def test_does_not_retry_a_404():
    calls = {"n": 0}

    def handler(request):
        calls["n"] += 1
        return httpx.Response(404, json={})

    with pytest.raises(httpx.HTTPStatusError):
        list(_source(handler).fetch("acme"))
    assert calls["n"] == 1
