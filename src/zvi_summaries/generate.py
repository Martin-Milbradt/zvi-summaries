import datetime
from email.utils import format_datetime
from xml.sax.saxutils import escape

from zvi_summaries.cache import CachedSummary

FEED_TEMPLATE = """\
<?xml version="1.0" encoding="utf-8"?>
<rss version="2.0" xmlns:dc="http://purl.org/dc/elements/1.1/">
  <channel>
    <title>Don't Worry About the Vase -- Summaries</title>
    <link>https://thezvi.substack.com</link>
    <description>LLM-generated 2-paragraph summaries of Zvi Mowshowitz's blog posts.</description>
    <language>en</language>
    <lastBuildDate>{last_build_date}</lastBuildDate>
{items}
  </channel>
</rss>
"""

ITEM_TEMPLATE = """\
    <item>
      <title>{title}</title>
      <link>{link}</link>
      <guid isPermaLink="false">{guid}</guid>
      <pubDate>{pub_date}</pubDate>
      <dc:creator>{author}</dc:creator>
      <description>{description}</description>
    </item>"""


def format_rfc822(dt: datetime.datetime) -> str:
    return format_datetime(dt)


def format_item(guid: str, summary: CachedSummary) -> str:
    pub_dt = datetime.datetime.fromisoformat(summary["pub_date"])
    return ITEM_TEMPLATE.format(
        title=escape(summary["title"]),
        link=escape(summary["link"]),
        guid=escape(guid),
        pub_date=format_rfc822(pub_dt),
        author=escape(summary["author"]),
        description=escape(summary["summary"]),
    )


def build_feed(summaries: dict[str, CachedSummary]) -> str:
    sorted_items = sorted(
        summaries.items(),
        key=lambda kv: kv[1]["pub_date"],
        reverse=True,
    )
    item_xmls = [format_item(guid, s) for guid, s in sorted_items]
    return FEED_TEMPLATE.format(
        last_build_date=format_rfc822(datetime.datetime.now(datetime.UTC)),
        items="\n".join(item_xmls),
    )
