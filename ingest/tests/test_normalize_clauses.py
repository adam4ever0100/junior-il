from junior_il.normalize import clauses


def test_degree_required():
    assert clauses.degree_required("B.Sc. in Computer Science or equivalent degree")
    assert clauses.degree_required("Bachelor's degree in Engineering")
    assert clauses.degree_required("תואר ראשון במדעי המחשב")


def test_degree_marked_optional_does_not_filter_anyone():
    assert not clauses.degree_required(
        "B.Sc. in Computer Science or equivalent practical experience"
    )
    assert not clauses.degree_required("A degree is a plus but not required")


def test_no_degree_mention():
    assert not clauses.degree_required("Strong Python skills and a portfolio")


def test_clearance_and_military_service():
    assert clauses.clearance_required("Security clearance required")
    assert clauses.clearance_required("סיווג ביטחוני נדרש")
    assert clauses.clearance_required("Valid IDF service is required")
    assert not clauses.clearance_required("Work with our defence-sector customers")


def test_empty_description():
    assert not clauses.degree_required("")
    assert not clauses.clearance_required("")
