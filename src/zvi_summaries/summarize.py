import collections.abc
import dataclasses
import os

import openai

DEFAULT_MODEL = "google/gemini-2.5-flash"
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

SYSTEM_PROMPT = """\
You are a concise summarizer of blog posts by Zvi Mowshowitz.
Write exactly two paragraphs summarizing the article.
The first paragraph should capture the main thesis or key developments discussed.
The second paragraph should cover the author's analysis, opinions, or conclusions.
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
    model: str = DEFAULT_MODEL,
) -> str:
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


def summarize_article(title: str, text: str) -> str:
    messages = [
        ChatMessage(role="system", content=SYSTEM_PROMPT),
        ChatMessage(
            role="user",
            content=f"Summarize this article.\n\nTitle: {title}\n\nContent:\n{text}",
        ),
    ]
    return post_chat(messages)
