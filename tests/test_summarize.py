from unittest.mock import patch

import pytest

from zvi_summaries.summarize import (
    MissingOpenRouterKeyError,
    environment_api_key,
    summarize_article,
)


def test_environment_api_key_missing() -> None:
    with patch.dict("os.environ", {}, clear=True):
        with pytest.raises(MissingOpenRouterKeyError):
            environment_api_key()


def test_environment_api_key_present() -> None:
    with patch.dict("os.environ", {"OPENROUTER_API_KEY": "test-key-123"}):
        assert environment_api_key() == "test-key-123"


def test_environment_api_key_strips_whitespace() -> None:
    with patch.dict("os.environ", {"OPENROUTER_API_KEY": "  key  "}):
        assert environment_api_key() == "key"


def test_summarize_article_prompt_structure() -> None:
    mock_summary = "Para one.\n\nPara two."

    with patch(
        "zvi_summaries.summarize.post_chat", return_value=mock_summary
    ) as mock_chat:
        result = summarize_article("Test Title", "Article body text here.")

    assert result == mock_summary

    messages = mock_chat.call_args[0][0]
    assert len(messages) == 2
    assert messages[0].role == "system"
    assert "four paragraphs" in messages[0].content
    assert messages[1].role == "user"
    assert "Test Title" in messages[1].content
    assert "Article body text here." in messages[1].content
