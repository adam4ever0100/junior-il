from junior_il.htmltext import html_to_text


def test_strips_tags_and_keeps_line_structure():
    html = "<p>We need <b>Python</b>.</p><ul><li>Docker</li><li>K8s</li></ul>"
    assert html_to_text(html) == "We need Python.\n\nDocker\n\nK8s"


def test_drops_script_and_style_content():
    assert "alert" not in html_to_text("<p>hi</p><script>alert(1)</script>")


def test_years_phrases_do_not_glue_to_previous_line():
    # The normalizer greps for this phrase; a missing break would hide it.
    text = html_to_text("<li>Backend role</li><li>5+ years of experience</li>")
    assert "5+ years of experience" in text
    assert "role5+" not in text


def test_handles_entities_and_nbsp():
    assert html_to_text("<p>Node&nbsp;&amp;&nbsp;Go</p>") == "Node & Go"


def test_empty_input():
    assert html_to_text("") == ""
