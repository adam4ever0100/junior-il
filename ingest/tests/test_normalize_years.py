"""Years-of-experience extraction, anchored on real posting text."""
from junior_il.normalize.years import find_all, summarize


def test_plain_plus_form():
    s = summarize("7+ years of experience as a Backend or Full Stack engineer")
    assert (s.stated, s.floor, s.bar) == (True, 7, 7)


def test_range_states_its_floor_not_its_ceiling():
    # "4-8 years" demands four. Reading the 8 as the requirement would also
    # brand "0-2 years" as closed to juniors, which is the opposite of true.
    assert summarize("4-8 years of professional experience").bar == 4
    assert summarize("0-2 years of experience").bar == 0


def test_en_dash_range_from_the_corpus():
    assert summarize("1–2+ years of experience working with websites").bar == 1


def test_at_least_and_minimum_forms():
    assert summarize("At least 5 years of experience with CI/CD pipelines").bar == 5
    assert summarize("Minimum 5 years of experience in a client facing role").bar == 5


def test_curly_apostrophe_after_years():
    assert summarize("8+ years’ experience with operating systems").bar == 8


def test_singular_year_typo_in_the_wild():
    assert summarize("4+ year of experience ideally in a Customer Success role").stated


def test_word_numbers():
    assert summarize("three years of hands-on experience").bar == 3


def test_the_steepest_requirement_is_the_bar():
    # A posting stacking requirements is a seven-year job, not a one-year job.
    text = "7+ years of experience in software\n1+ years of experience with Kafka"
    s = summarize(text)
    assert (s.floor, s.bar) == (1, 7)


def test_a_plus_in_a_parenthetical_does_not_demote_the_requirement():
    # Real posting: the "a plus" governs Go, not the six years. Treating the
    # whole line as preferred dropped this role from the counts entirely.
    text = "6+ years of backend development experience using Java (Go is a plus)."
    s = summarize(text)
    assert s.stated and s.bar == 6


def test_a_plus_governing_the_years_does_demote_it():
    assert not summarize("5+ years with Kafka is an advantage").stated
    assert not summarize("Nice to have: 2+ years of Go").stated


def test_years_inside_its_own_parenthetical_keep_that_scope():
    assert not summarize("Strong backend skills (5+ years is a plus)").stated


def test_history_phrases_are_not_requirements():
    assert not summarize("Our platform has grown 10x in the last 3 years").stated
    assert not summarize("The company was founded 10 years ago").stated


def test_silence_is_not_zero():
    s = summarize("We are looking for a talented backend engineer.")
    assert s.stated is False and s.floor is None and s.bar is None


def test_several_years_is_a_requirement_without_a_number():
    # Real posting: "Several years of hands-on experience in application
    # security". Falling through to stated=False would read as "no experience
    # required" and count the role as open to a graduate.
    s = summarize("Several years of hands-on experience in application security")
    assert s.vague is True
    assert s.stated is False   # no number to report
    assert s.evidence == "Several years"


def test_implausible_figures_are_ignored():
    assert not summarize("100 years of combined team experience").stated


def test_evidence_records_the_phrase_that_set_the_bar():
    s = summarize("2+ years of SQL\n9+ years of distributed systems")
    assert s.bar == 9 and "9" in s.evidence


def test_findings_expose_the_preferred_ones_for_auditing():
    found = find_all("5+ years required\n3+ years of Rust is a plus")
    assert [(f.threshold, f.required) for f in found] == [(5, True), (3, False)]


def test_empty_description():
    s = summarize("")
    assert s.stated is False and s.vague is False
