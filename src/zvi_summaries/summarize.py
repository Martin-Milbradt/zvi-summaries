import collections.abc
import dataclasses
import os

import openai

DEFAULT_MODEL = "anthropic/claude-opus-4-6"
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"


def configured_model() -> str:
    """Model id to use, overridable via the SUMMARY_MODEL env var."""
    return os.environ.get("SUMMARY_MODEL", "").strip() or DEFAULT_MODEL


SYSTEM_PROMPT = """\
You are a concise summarizer of blog posts by Zvi Mowshowitz.
Write exactly four paragraphs summarizing the article.
The first paragraph should capture the main thesis or topic of the article.
The second paragraph should cover the key developments, facts, or arguments presented.
The third paragraph should describe the author's analysis, opinions, or conclusions.
The fourth paragraph should note any actionable takeaways, open questions, or implications.
Do not use bullet points or headers. Write in plain prose.
Do not editorialize beyond what the author wrote."""


@dataclasses.dataclass(frozen=True)
class ChatMessage:
    role: str
    content: str


class MissingOpenRouterKeyError(Exception):
    pass


class OpenRouterRequestError(Exception):
    pass


def environment_api_key() -> str:
    token = os.environ.get("OPENROUTER_API_KEY", "").strip()
    if token:
        return token
    raise MissingOpenRouterKeyError("Set the OPENROUTER_API_KEY environment variable.")


def serialize_messages(
    messages: collections.abc.Sequence[ChatMessage],
) -> list[dict[str, str]]:
    return [{"role": m.role, "content": m.content} for m in messages]


def post_chat(
    messages: collections.abc.Sequence[ChatMessage],
    model: str | None = None,
) -> str:
    model = model or configured_model()
    api_key = environment_api_key()
    client = openai.OpenAI(
        base_url=OPENROUTER_BASE_URL,
        api_key=api_key,
        timeout=120.0,
    )
    response = client.chat.completions.create(
        model=model,
        messages=serialize_messages(messages),  # pyright: ignore[reportArgumentType]
    )
    content = response.choices[0].message.content
    if not content:
        raise OpenRouterRequestError("OpenRouter response contained empty content.")
    return content


def summarize_article(title: str, text: str, model: str | None = None) -> str:
    messages = [
        ChatMessage(role="system", content=SYSTEM_PROMPT),
        ChatMessage(
            role="user",
            content=f"Summarize this article.\n\nTitle: {title}\n\nContent:\n{text}",
        ),
    ]
    return post_chat(messages, model=model or configured_model())
