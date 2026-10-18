"""Title rules, including the false positives this corpus actually contains."""
from junior_il.normalize import titles


def test_word_boundary_stops_internal_matching_intern():
    # Real posting. "Internal" contains "intern"; without a word boundary this
    # director-level role reads as an internship.
    title = "Director of AI Engineering, Internal Products"
    assert not titles.junior_signal(title)
    assert titles.seniority(title) == titles.MANAGER


def test_product_name_containing_student_is_caught_by_the_other_rules():
    # Real posting: "Via Student Transit" is a product. The title does say
    # "Student", so junior_signal fires — the seniority and engineering rules
    # are what keep it out of the junior-eligible pool.
    title = "Field Operations Manager, Via Student Transit"
    assert titles.junior_signal(title)
    assert titles.seniority(title) == titles.MANAGER
    assert not titles.is_engineering(title)


def test_the_one_junior_titled_israeli_posting_is_not_engineering():
    # The entire junior-titled Israeli sample, September and October both.
    title = "Employer Branding Student (Temporary )"
    assert titles.junior_signal(title)
    assert not titles.is_engineering(title)


def test_seniority_ordering_puts_manager_above_senior():
    assert titles.seniority("Senior Engineering Manager") == titles.MANAGER
    assert titles.seniority("Principal Tech Lead (Backend oriented)") == titles.MANAGER or \
           titles.seniority("Principal Tech Lead (Backend oriented)") == titles.LEAD


def test_plain_titles_are_unspecified_not_junior():
    # The large middle of the market: no seniority word at all. Calling these
    # junior would invent an open door; the years rules decide them instead.
    assert titles.seniority("Software Engineer") == titles.UNSPECIFIED
    assert titles.seniority("SW Engineer - Enterprise Browser team") == titles.UNSPECIFIED


def test_junior_titles():
    for title in ["Junior Backend Engineer", "Jr. Software Engineer",
                  "Graduate Software Engineer", "Entry-Level QA Engineer",
                  "Software Engineering Intern"]:
        assert titles.junior_signal(title), title
        assert titles.seniority(title) == titles.JUNIOR, title


def test_hebrew_titles():
    assert titles.is_engineering("מפתח Backend")
    assert titles.junior_signal("מתמחה פיתוח")
    assert titles.seniority("מנהל פיתוח") == titles.MANAGER


def test_qa_and_automation_count_as_engineering():
    # A deliberate inclusion: these are engineering jobs, and one of the few
    # routes in this market that opens to a graduate at all.
    for title in ["QA Automation Engineer", "SDET", "Test Engineer",
                  "Software QA Engineer"]:
        assert titles.is_engineering(title), title


def test_customer_facing_engineer_titles_are_excluded():
    for title in ["Sales Engineer", "Solutions Engineer", "Technical Support Engineer",
                  "Customer Success Engineer", "Solutions Architect"]:
        assert not titles.is_engineering(title), title


def test_non_engineering_titles():
    for title in ["Account Executive", "Employer Branding Student",
                  "Product Manager", "Recruiter", "Finance Analyst"]:
        assert not titles.is_engineering(title), title


def test_engineering_department_can_carry_a_title_with_no_role_word():
    assert titles.is_engineering("Backend - Core", department="R&D")
    assert not titles.is_engineering("Office Manager", department="R&D")
