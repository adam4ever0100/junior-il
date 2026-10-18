"""Location rules. Every string here appeared in the real corpus."""
from junior_il.normalize.location import classify, segments


def israel(text):
    return classify(text)[0]


def cities(text):
    return classify(text)[1]


def test_the_most_common_israeli_string_has_no_country_in_it():
    # "Tel Aviv" was the single most common location in the corpus, and the
    # reason a `location_raw ILIKE '%israel%'` filter missed 42% of the market.
    assert israel("Tel Aviv")
    assert cities("Tel Aviv") == ["Tel Aviv"]


def test_country_spellings_and_district_forms():
    assert israel("Tel Aviv District, Israel")
    assert israel("Tel Aviv, Israel")
    assert israel("Israel - Raanana")
    assert israel("Tel Aviv-Yafo, Tel Aviv District, Israel")


def test_hyphen_inside_a_city_name_is_not_a_separator():
    # Splitting on a bare hyphen would cut "Tel Aviv-Yafo" in half.
    assert cities("Tel Aviv-Yafo") == ["Tel Aviv"]
    assert israel("Beer-Sheva")


def test_curly_apostrophe_from_the_corpus():
    # Stored as "Giv‘atayim, Tel Aviv, Israel".
    assert israel("Giv‘atayim, Tel Aviv, Israel")
    assert "Givatayim" in cities("Giv‘atayim, Tel Aviv, Israel")


def test_hebrew_location():
    assert israel("תל אביב")
    assert israel("באר שבע")


def test_multi_city_strings_count_if_any_segment_is_israeli():
    assert israel("Glilot; Tel Aviv")
    assert israel("Tel Aviv/ Netanya, Israel")
    assert sorted(cities("Tel Aviv/ Netanya, Israel")) == ["Netanya", "Tel Aviv"]


def test_foreign_locations_are_not_israel():
    for text in [
        "New York City (NYC), New York, United States", "USA - Remote",
        "London, England, United Kingdom", "India - Pune", "Tokyo Prefecture, Japan",
        "Sacramento, CA; San Jose, CA; Santa Rosa, CA", "Dubai", "Prague, Czech Republic",
    ]:
        assert not israel(text), text


def test_acre_is_not_matched_because_of_the_brazilian_state():
    # "Akko" is the Israeli city; "Acre" is also a state in Brazil, so the
    # English alias is deliberately absent.
    assert not israel("Acre, Brazil")
    assert israel("Akko")


def test_remote_detection_does_not_imply_israel():
    in_israel, _, remote = classify("USA - Remote")
    assert remote and not in_israel


def test_segments_drops_empty_pieces():
    assert segments("Tel Aviv,, ; Haifa") == ["Tel Aviv", "Haifa"]


def test_empty_location():
    assert classify("") == (False, [], False)
