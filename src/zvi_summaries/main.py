import argparse
import datetime
from pathlib import Path
from typing import cast

from zvi_summaries.cache import CachedSummary, load_cache, save_cache
from zvi_summaries.fetch import fetch_articles, strip_html
from zvi_summaries.generate import build_feed
from zvi_summaries.summarize import summarize_article

DEFAULT_CACHE_PATH = Path("data/cache.json")
DEFAULT_OUTPUT_PATH = Path("docs/feed.xml")


def run(
    cache_path: Path = DEFAULT_CACHE_PATH,
    output_path: Path = DEFAULT_OUTPUT_PATH,
) -> int:
    """Returns the number of newly summarized articles."""
    cache = load_cache(cache_path)
    articles = fetch_articles()

    new_count = 0
    for article in articles:
        if article.guid in cache:
            continue

        print(f"Summarizing: {article.title}")  # noqa: T201
        text = strip_html(article.content_html)
        summary = summarize_article(article.title, text)

        cache[article.guid] = CachedSummary(
            title=article.title,
            link=article.link,
            author=article.author,
            pub_date=article.pub_date.isoformat(),
            summary=summary,
            summarized_at=datetime.datetime.now(datetime.UTC).isoformat(),
        )
        new_count += 1

        # Save after each article so partial runs preserve progress
        save_cache(cache_path, cache)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        _ = f.write(build_feed(cache))

    print(f"Done. {new_count} new summaries. Total: {len(cache)}.")  # noqa: T201
    return new_count


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate summarized RSS feed")
    _ = parser.add_argument("--cache", type=Path, default=DEFAULT_CACHE_PATH)
    _ = parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH)
    args = parser.parse_args()
    cache_path = cast(Path, args.cache)
    output_path = cast(Path, args.output)
    _ = run(cache_path=cache_path, output_path=output_path)


if __name__ == "__main__":
    main()
