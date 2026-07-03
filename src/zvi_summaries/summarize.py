import collections.abc
import dataclasses
import datetime
import os

import openai

DEFAULT_KNOWLEDGE_CUTOFF = "January 2026"
DEFAULT_MODEL = "anthropic/claude-opus-4.8"
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"


def configured_model() -> str:
    """Model id to use: SUMMARY_MODEL (CI) wins, then the global LLM_STRONG tier, then the default."""
    return (
        os.environ.get("SUMMARY_MODEL", "").strip()
        or os.environ.get("LLM_STRONG", "").strip()
        or DEFAULT_MODEL
    )


def configured_knowledge_cutoff() -> str:
    """Cutoff stated in the prompt: KNOWLEDGE_CUTOFF (CI) wins, then the default."""
    return os.environ.get("KNOWLEDGE_CUTOFF", "").strip() or DEFAULT_KNOWLEDGE_CUTOFF


SYSTEM_PROMPT_TEMPLATE = """\
You summarize blog posts by Zvi Mowshowitz.
Write exactly four paragraphs of plain prose: no bullet points, headers, or editorializing beyond what the author wrote.
Your knowledge cutoff is {knowledge_cutoff} and today is {today}; the article may cover events after your cutoff, so trust its account over your priors."""


def system_prompt() -> str:
    return SYSTEM_PROMPT_TEMPLATE.format(
        knowledge_cutoff=configured_knowledge_cutoff(),
        today=datetime.date.today().isoformat(),
    )


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
        ChatMessage(role="system", content=system_prompt()),
        ChatMessage(
            role="user",
            content=f"Summarize this article.\n\nTitle: {title}\n\nContent:\n{text}",
        ),
    ]
    return post_chat(messages, model=model or configured_model())
