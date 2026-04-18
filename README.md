# zvi-summaries

RSS feed of LLM-generated 2-paragraph summaries of [thezvi.substack.com](https://thezvi.substack.com) articles.

## Feed

Subscribe: <https://martin-milbradt.github.io/zvi-summaries/feed.xml>

## Usage

```bash
uv sync --dev                    # Install dependencies
uv run zvi-summaries              # Run pipeline (requires OPENROUTER_API_KEY)
uv run pytest                     # Run tests
uv run ruff check src/ tests/     # Lint
uv run ruff format src/ tests/    # Format
uv run basedpyright src/          # Type check
```

## How it works

Fetches the Substack RSS feed, summarizes uncached articles via OpenRouter, and writes the result to `docs/feed.xml` (served by GitHub Pages). Summaries are cached in `data/cache.json`.
