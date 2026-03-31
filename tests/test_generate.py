import xml.etree.ElementTree as ET

from zvi_summaries.cache import CachedSummary
from zvi_summaries.generate import build_feed


def make_summary(
    title: str = "Test",
    pub_date: str = "2026-03-15T12:00:00+00:00",
) -> CachedSummary:
    return CachedSummary(
        title=title,
        link="https://thezvi.substack.com/p/test",
        author="Zvi Mowshowitz",
        pub_date=pub_date,
        summary="First paragraph.\n\nSecond paragraph.",
        summarized_at="2026-03-15T14:00:00+00:00",
    )


def test_build_feed_valid_xml() -> None:
    summaries = {"guid-1": make_summary("Article One")}
    xml_str = build_feed(summaries)

    # Should parse without error
    root = ET.fromstring(xml_str)
    assert root.tag == "rss"
    assert root.attrib["version"] == "2.0"


def test_build_feed_contains_items() -> None:
    summaries = {
        "guid-1": make_summary("First"),
        "guid-2": make_summary("Second"),
    }
    xml_str = build_feed(summaries)
    root = ET.fromstring(xml_str)

    items = root.findall(".//item")
    assert len(items) == 2


def test_build_feed_sorted_newest_first() -> None:
    summaries = {
        "old": make_summary("Old Post", pub_date="2026-01-01T00:00:00+00:00"),
        "new": make_summary("New Post", pub_date="2026-03-15T00:00:00+00:00"),
    }
    xml_str = build_feed(summaries)
    root = ET.fromstring(xml_str)

    items = root.findall(".//item")
    titles = [item.find("title").text for item in items]  # type: ignore[union-attr]
    assert titles == ["New Post", "Old Post"]


def test_build_feed_escapes_special_chars() -> None:
    summaries = {
        "guid-1": make_summary('Title with <angle> & "quotes"'),
    }
    xml_str = build_feed(summaries)
    # Should still parse as valid XML
    root = ET.fromstring(xml_str)
    item = root.find(".//item")
    assert item is not None
    title = item.find("title")
    assert title is not None
    assert title.text == 'Title with <angle> & "quotes"'


def test_build_feed_empty() -> None:
    xml_str = build_feed({})
    root = ET.fromstring(xml_str)
    items = root.findall(".//item")
    assert items == []
