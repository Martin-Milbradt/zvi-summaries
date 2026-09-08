# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportMissingTypeStubs=false
import dataclasses
import datetime
import re
import time
from typing import cast

import feedparser
from bs4 import BeautifulSoup, Tag

FEED_URL = "https://thezvi.wordpress.com/feed/"
USER_AGENT = (
    "Mozilla/5.0 (zvi-summaries; +https://github.com/Martin-Milbradt/zvi-summaries)"
)
# Guard rail against a runaway feed payload, not a budget: the longest posts run
# about 100k characters, so real articles never hit it.
MAX_TEXT_LENGTH = 400_000
# Tags that end a paragraph: a blank line before and after.
PARAGRAPH_TAGS = [
    "blockquote",
    "div",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "ol",
    "p",
    "pre",
    "table",
    "ul",
]
# Tags that end a line within a paragraph-level block.
LINE_TAGS = ["br", "hr", "li", "tr"]


class FeedFetchError(Exception):
    pass


@dataclasses.dataclass(frozen=True)
class Article:
    guid: str
    title: str
    link: str
    author: str
    pub_date: datetime.datetime
    content_html: str


def fetch_articles(url: str = FEED_URL) -> list[Article]:
    feed = feedparser.parse(url, agent=USER_AGENT)

    status = cast(int | None, getattr(feed, "status", None))
    bozo = bool(getattr(feed, "bozo", False))
    bozo_exception = getattr(feed, "bozo_exception", None)
    entries = cast(list[object], feed.entries)
    print(f"Feed status={status} bozo={bozo} entries={len(entries)}")  # noqa: T201

    if status is not None and status >= 400:
        raise FeedFetchError(f"Feed request returned HTTP {status} for {url}.")
    if bozo and not entries:
        raise FeedFetchError(f"Feed parse failed for {url}: {bozo_exception!r}")
    if not entries:
        raise FeedFetchError(
            f"Feed returned zero entries for {url} (likely blocked or empty)."
        )

    articles: list[Article] = []
    for entry in feed.entries:
        content_html = ""
        if entry.get("content"):
            content_html = cast(str, entry["content"][0].get("value", ""))
        if not content_html:
            content_html = cast(str, entry.get("summary", ""))

        pub_date = datetime.datetime.now(datetime.UTC)
        parsed = cast(
            time.struct_time | None,
            entry.get("published_parsed") or entry.get("updated_parsed"),
        )
        if parsed:
            pub_date = datetime.datetime(*parsed[:6], tzinfo=datetime.UTC)

        articles.append(
            Article(
                guid=cast(str, entry.get("id", entry.get("link", ""))),
                title=cast(str, entry.get("title", "")),
                link=cast(str, entry.get("link", "")),
                author=cast(str, entry.get("author", "Zvi Mowshowitz")),
                pub_date=pub_date,
                content_html=content_html,
            )
        )
    return articles


def block_text(root: Tag) -> str:
    """Text of a subtree: newlines at block boundaries only, inline markup joined."""
    # get_text(separator) would also split at inline tags like <a> and <strong>,
    # scattering one sentence over several lines, so only block boundaries break.
    for tag in root.find_all(PARAGRAPH_TAGS):
        _ = tag.insert_before("\n\n")
        _ = tag.insert_after("\n\n")
    for tag in root.find_all(LINE_TAGS):
        _ = tag.insert_after("\n")

    text = root.get_text().replace("\u200b", "")
    lines = (" ".join(line.split()) for line in text.split("\n"))
    return re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()


def strip_html(html: str, max_length: int = MAX_TEXT_LENGTH) -> str:
    """Article as light markdown: `#` headings, list markers, `>` quotes, `[image]`."""
    soup = BeautifulSoup(html, "lxml")

    for tag in soup.find_all(["script", "style", "svg"]):
        tag.decompose()

    # Remove Substack subscription widgets
    for div in soup.find_all("div", class_=re.compile(r"subscription-widget")):
        div.decompose()

    # Formatting whitespace between tags would otherwise put blank lines between
    # list items.
    for node in soup.find_all(string=True):
        if "\n" in node and not node.strip():
            _ = node.replace_with(" ")

    # A placeholder keeps sentences like "this chart shows" pointing at something.
    # Images come double-wrapped in <figure>, so only the outer one is replaced.
    for figure in soup.find_all("figure"):
        if figure.find_parent("figure"):
            continue
        caption = figure.find("figcaption")
        label = (
            f"[image: {caption.get_text(' ', strip=True)}]" if caption else "[image]"
        )
        _ = figure.replace_with(f"\n\n{label}\n\n")

    # Emoji arrive as <img> tags with the character in alt.
    for img in soup.find_all("img"):
        _ = img.replace_with(cast(str, img.get("alt", "")) or "[image]")

    for heading in soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6"]):
        _ = heading.insert(0, "#" * int(heading.name[1]) + " ")
    for ordered in soup.find_all("ol"):
        for number, item in enumerate(ordered.find_all("li", recursive=False), 1):
            _ = item.insert(0, f"{number}. ")
    for unordered in soup.find_all("ul"):
        for item in unordered.find_all("li", recursive=False):
            _ = item.insert(0, "- ")

    # <blockquote> is how the author marks quoted material. Innermost first, so a
    # quote inside a quote comes out as "> > ".
    for quote in reversed(soup.find_all("blockquote")):
        quoted = "\n".join(
            f"> {line}".rstrip() for line in block_text(quote).split("\n")
        )
        _ = quote.replace_with(f"\n\n{quoted}\n\n")

    text = block_text(soup)

    if len(text) > max_length:
        print(  # noqa: T201
            f"  WARNING: text truncated from {len(text):,} to {max_length:,} chars"
        )
        text = text[:max_length] + "\n\n[Content truncated]"

    return text
