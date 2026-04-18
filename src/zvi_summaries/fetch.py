# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportMissingTypeStubs=false
import dataclasses
import datetime
import re
import time
from typing import cast

import feedparser
from bs4 import BeautifulSoup

FEED_URL = "https://thezvi.wordpress.com/feed/"
USER_AGENT = (
    "Mozilla/5.0 (zvi-summaries; +https://github.com/Martin-Milbradt/zvi-summaries)"
)


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


def strip_html(html: str, max_length: int = 15_000) -> str:
    soup = BeautifulSoup(html, "lxml")

    # Remove non-content elements
    for tag in soup.find_all(["script", "style", "img", "figure", "svg"]):
        tag.decompose()

    # Remove Substack subscription widgets
    for div in soup.find_all("div", class_=re.compile(r"subscription-widget")):
        div.decompose()

    text = soup.get_text(separator="\n")

    # Collapse multiple blank lines
    text = re.sub(r"\n{3,}", "\n\n", text).strip()

    if len(text) > max_length:
        text = text[:max_length] + "\n\n[Content truncated]"

    return text
