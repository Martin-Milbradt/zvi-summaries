import argparse
import datetime
from pathlib import Path
from typing import cast

from zvi_summaries.cache import CachedSummary, load_cache, save_cache
from zvi_summaries.fetch import FEED_URL, Article, fetch_articles, strip_html
from zvi_summaries.generate import build_feed
from zvi_summaries.summarize import (
    ArticleRefusedError,
    configured_fallback_model,
    configured_model,
    summarize_with_fallback,
)

DEFAULT_CACHE_PATH = Path("data/cache.json")
DEFAULT_OUTPUT_PATH = Path("docs/feed.xml")


class RefusedArticlesError(Exception):
    pass


def fetch_pages(pages: int) -> list[Article]:
    """Articles from the newest feed page, plus older pages so gaps stay recoverable."""
    articles = fetch_articles()
    seen = {a.guid for a in articles}
    for page in range(2, pages + 1):
        for article in fetch_articles(f"{FEED_URL}?paged={page}"):
            if article.guid not in seen:
                seen.add(article.guid)
                articles.append(article)
    return articles


def run(
    cache_path: Path = DEFAULT_CACHE_PATH,
    output_path: Path = DEFAULT_OUTPUT_PATH,
    pages: int = 1,
) -> int:
    """Returns the number of newly summarized articles."""
    cache = load_cache(cache_path)
    articles = fetch_pages(pages)
    model = configured_model()
    fallback = configured_fallback_model()

    new_count = 0
    refused: list[str] = []
    for article in articles:
        if article.guid in cache:
            continue

        print(f"Summarizing: {article.title}")  # noqa: T201
        text = strip_html(article.content_html)
        # Refusals must not abort the run: the remaining articles are still
        # summarizable, and the feed only recovers if they get written.
        try:
            summary, used_model = summarize_with_fallback(
                article.title, text, model, fallback
            )
        except ArticleRefusedError as exc:
            print(f"  REFUSED: {exc}")  # noqa: T201
            refused.append(article.title)
            continue

        cache[article.guid] = CachedSummary(
            title=article.title,
            link=article.link,
            author=article.author,
            pub_date=article.pub_date.isoformat(),
            summary=summary,
            summarized_at=datetime.datetime.now(datetime.UTC).isoformat(),
            model=used_model,
        )
        new_count += 1

        # Save after each article so partial runs preserve progress
        save_cache(cache_path, cache)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        _ = f.write(build_feed(cache))

    print(f"Done. {new_count} new summaries. Total: {len(cache)}.")  # noqa: T201

    # Raised last, so the cache and feed above are already written: the workflow
    # commits them regardless, and the failure still surfaces as a notification.
    if refused:
        raise RefusedArticlesError(
            f"{len(refused)} article(s) refused by the model: {'; '.join(refused)}"
        )
    return new_count


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate summarized RSS feed")
    _ = parser.add_argument("--cache", type=Path, default=DEFAULT_CACHE_PATH)
    _ = parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH)
    _ = parser.add_argument(
        "--pages",
        type=int,
        default=1,
        help="Feed pages to scan; >1 recovers posts that scrolled out of page 1.",
    )
    args = parser.parse_args()
    cache_path = cast(Path, args.cache)
    output_path = cast(Path, args.output)
    pages = cast(int, args.pages)
    _ = run(cache_path=cache_path, output_path=output_path, pages=pages)


if __name__ == "__main__":
    main()
