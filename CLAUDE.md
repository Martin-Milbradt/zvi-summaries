# zvi-summaries

RSS feed of LLM-generated 2-paragraph summaries of thezvi.substack.com articles.

## Commands

```bash
uv sync --dev                                    # Install dependencies
uv run zvi-summaries                             # Run the pipeline (needs OPENROUTER_API_KEY)
uv run pytest                                    # Run tests
uv run ruff check src/ tests/                    # Lint
uv run ruff format src/ tests/                   # Format
uv run basedpyright src/                         # Type check
```

## Architecture

Pipeline: fetch Substack RSS -> filter uncached articles -> summarize via OpenRouter -> write cache + feed XML.

- `src/zvi_summaries/fetch.py` -- download and parse the Substack RSS feed, strip HTML
- `src/zvi_summaries/summarize.py` -- OpenRouter client, summarization prompt
- `src/zvi_summaries/cache.py` -- JSON cache of article summaries
- `src/zvi_summaries/generate.py` -- build RSS 2.0 XML from cache
- `src/zvi_summaries/main.py` -- CLI entry point

## Output

- `data/cache.json` -- persisted summaries (committed)
- `docs/feed.xml` -- generated RSS feed (served by GitHub Pages)

## Environment

- `OPENROUTER_API_KEY` -- required for LLM summarization
