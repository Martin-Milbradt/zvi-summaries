# zvi-summaries

RSS feed of LLM-generated four-paragraph summaries of Zvi Mowshowitz's blog. Posts come from the WordPress mirror feed (`FEED_URL` in `fetch.py`), which serves full post bodies without comments; the Substack feed returns 403 to GitHub Actions runners.

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

Pipeline: fetch the RSS feed -> filter uncached articles -> summarize via OpenRouter -> write cache + feed XML.

A model may refuse an article under its content policy. The run retries once on `FALLBACK_MODEL`, keeps going past articles both models refuse, and raises `RefusedArticlesError` only after the cache and feed are written, so a failure still commits the summaries that succeeded and still sends a workflow-failure notification.

- `src/zvi_summaries/fetch.py` -- download and parse the RSS feed, strip HTML
- `src/zvi_summaries/summarize.py` -- OpenRouter client, summarization prompt
- `src/zvi_summaries/cache.py` -- JSON cache of article summaries
- `src/zvi_summaries/generate.py` -- build RSS 2.0 XML from cache
- `src/zvi_summaries/main.py` -- CLI entry point

Articles go to the model whole. `MAX_TEXT_LENGTH` in `fetch.py` only guards against a runaway payload; the longest posts reach about a quarter of it. The run log prints each article's character count. The text is light markdown: `#` headings, `1.` and `-` list markers, `>` on block quotes (the author's marker for quoted material, so the model can tell the author's words from quoted text), and an `[image]` placeholder where a figure was, so a sentence like "this chart shows" still points at something.

## Output

- `data/cache.json` -- persisted summaries (committed)
- `docs/feed.xml` -- generated RSS feed (served by GitHub Pages)

## Environment

- `OPENROUTER_API_KEY` -- required for LLM summarization
- `SUMMARY_MODEL` -- model id; the CI repo variable wins, then the global `LLM_MAX` tier. With neither set, `configured_model()` raises `MissingModelError` rather than picking one.
- `FALLBACK_MODEL` -- model retried when `SUMMARY_MODEL` refuses an article; the CI repo variable wins, then the global `LLM_STRONG` tier. Unset means no retry. Refusals are per-model, not per-provider, so a sibling model from the same provider is a valid choice.
- `KNOWLEDGE_CUTOFF` -- optional cutoff stated in the prompt (CI repo variable), defaults to `DEFAULT_KNOWLEDGE_CUTOFF`. It describes the configured model, so revisit it when `SUMMARY_MODEL` changes.

`--pages N` scans older feed pages as well as the newest. The feed holds only 10 entries, so an outage longer than 10 posts drops articles out of reach; `--pages 2` recovers them.
