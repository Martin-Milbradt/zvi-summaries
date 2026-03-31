from zvi_summaries.fetch import strip_html


def test_strip_html_basic() -> None:
    html = "<p>Hello <strong>world</strong>.</p><p>Second paragraph.</p>"
    result = strip_html(html)
    assert "Hello" in result
    assert "world" in result
    assert "Second paragraph." in result


def test_strip_html_removes_images() -> None:
    html = '<p>Before</p><img src="photo.jpg"><p>After</p>'
    result = strip_html(html)
    assert "Before" in result
    assert "After" in result
    assert "photo.jpg" not in result


def test_strip_html_removes_subscription_widget() -> None:
    html = (
        "<p>Content here.</p>"
        '<div class="subscription-widget-wrap"><p>Subscribe now</p></div>'
        "<p>More content.</p>"
    )
    result = strip_html(html)
    assert "Content here." in result
    assert "More content." in result
    assert "Subscribe" not in result


def test_strip_html_removes_script_and_style() -> None:
    html = "<style>body{color:red}</style><script>alert(1)</script><p>Text</p>"
    result = strip_html(html)
    assert "Text" in result
    assert "color:red" not in result
    assert "alert" not in result


def test_strip_html_truncation() -> None:
    html = "<p>" + "a" * 20_000 + "</p>"
    result = strip_html(html, max_length=100)
    assert len(result) < 200
    assert "[Content truncated]" in result


def test_strip_html_no_truncation_within_limit() -> None:
    html = "<p>Short text</p>"
    result = strip_html(html, max_length=1000)
    assert "[Content truncated]" not in result


def test_strip_html_collapses_blank_lines() -> None:
    html = "<p>One</p><br><br><br><br><p>Two</p>"
    result = strip_html(html)
    # Should not have more than one blank line between paragraphs
    assert "\n\n\n" not in result
