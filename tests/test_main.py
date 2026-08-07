import datetime
from pathlib import Path
from unittest.mock import patch

import pytest

from zvi_summaries.cache import load_cache
from zvi_summaries.fetch import Article
from zvi_summaries.main import RefusedArticlesError, fetch_pages, run
from zvi_summaries.summarize import ArticleRefusedError


def make_article(guid: str, title: str) -> Article:
    return Article(
        guid=guid,
        title=title,
        link=f"https://example.com/{guid}",
        author="Zvi Mowshowitz",
        pub_date=datetime.datetime(2026, 7, 20, tzinfo=datetime.UTC),
        content_html="<p>Body text.</p>",
    )


def test_run_writes_survivors_then_raises_on_refusal(tmp_path: Path) -> None:
    articles = [make_article("a", "Refused"), make_article("b", "Fine")]

    def fake_summarize(
        title: str, text: str, model: str, fallback: str | None
    ) -> tuple[str, str]:
        if title == "Refused":
            raise ArticleRefusedError("blocked under usage policy")
        return "Summary body.", model

    cache_path = tmp_path / "cache.json"
    output_path = tmp_path / "feed.xml"
    with (
        patch("zvi_summaries.main.fetch_pages", return_value=articles),
        patch("zvi_summaries.main.configured_model", return_value="test/model"),
        patch("zvi_summaries.main.configured_fallback_model", return_value=None),
        patch("zvi_summaries.main.summarize_with_fallback", side_effect=fake_summarize),
        pytest.raises(RefusedArticlesError, match="Refused"),
    ):
        _ = run(cache_path=cache_path, output_path=output_path)

    # The refusal must not cost us the article that did summarize.
    cache = load_cache(cache_path)
    assert set(cache) == {"b"}
    assert "Summary body." in output_path.read_text(encoding="utf-8")


def test_fetch_pages_deduplicates_across_pages() -> None:
    page_one = [make_article("a", "One"), make_article("b", "Two")]
    page_two = [make_article("b", "Two"), make_article("c", "Three")]

    def fake_fetch(url: str | None = None) -> list[Article]:
        return page_two if url and "paged=2" in url else page_one

    with patch("zvi_summaries.main.fetch_articles", side_effect=fake_fetch):
        assert [a.guid for a in fetch_pages(2)] == ["a", "b", "c"]


def test_fetch_pages_single_page_skips_pagination() -> None:
    with patch(
        "zvi_summaries.main.fetch_articles", return_value=[make_article("a", "One")]
    ) as fetch:
        assert len(fetch_pages(1)) == 1
    assert fetch.call_count == 1
