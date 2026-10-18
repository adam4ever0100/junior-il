"""The eligibility verdict — the one field the published number rests on."""
from junior_il.normalize import GRADUATE_YEARS, PARSER_VERSION, normalize_posting


def row(**kw):
    base = dict(id=1, source="greenhouse", board_token="acme", company="Acme",
                title="Software Engineer", location_raw="Tel Aviv",
                department="R&D", description="", url="")
    base.update(kw)
    return base


def test_a_plain_israeli_engineering_role_with_no_years_is_eligible():
    n = normalize_posting(row(description="Join our backend team."))
    assert n.is_israel and n.is_engineering and n.junior_eligible
    assert n.parser_version == PARSER_VERSION


def test_a_single_steep_requirement_closes_the_door():
    n = normalize_posting(row(description="1+ years of SQL\n5+ years of backend"))
    assert n.years_bar == 5 and not n.junior_eligible


def test_one_year_is_treated_as_within_reach_of_a_graduate():
    n = normalize_posting(row(description="1+ years of experience"))
    assert GRADUATE_YEARS == 1
    assert n.junior_eligible


def test_vague_years_closes_the_door_even_without_a_number():
    n = normalize_posting(row(description="Several years of hands-on experience"))
    assert n.years_vague and not n.years_stated and not n.junior_eligible


def test_senior_title_is_not_eligible_even_with_no_stated_years():
    # Real shape: Island's senior postings state no years at all.
    n = normalize_posting(row(title="Senior Backend Engineer- Tel Aviv",
                              description="Build our backend."))
    assert not n.years_stated and not n.junior_eligible


def test_foreign_roles_are_never_eligible():
    n = normalize_posting(row(location_raw="New York City", description="Entry level role"))
    assert not n.is_israel and not n.junior_eligible


def test_non_engineering_israeli_junior_roles_are_not_eligible():
    n = normalize_posting(row(title="Employer Branding Student (Temporary )",
                              location_raw="Israel - Raanana", department="People",
                              description="A student position."))
    assert n.junior_signal and not n.is_engineering and not n.junior_eligible


def test_junior_title_with_a_real_years_bar_is_still_not_eligible_for_a_graduate():
    # Common in Israel: the title says junior, the body asks for two years.
    # Reporting it as open would be the flattering answer, not the true one.
    n = normalize_posting(row(title="Junior Backend Engineer",
                              description="2+ years of experience with Node"))
    assert n.junior_signal and n.years_bar == 2 and not n.junior_eligible


def test_degree_and_clearance_are_recorded_but_do_not_decide_eligibility():
    # Kept out of the verdict on purpose: the headline number must not depend
    # on reading a "military service" mention correctly.
    n = normalize_posting(row(description="B.Sc. required. Security clearance required."))
    assert n.degree_required and n.clearance_required
    assert n.junior_eligible
