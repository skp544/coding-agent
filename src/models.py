from dataclasses import dataclass
from dotenv import load_dotenv
import os
from langchain_openai import ChatOpenAI

load_dotenv()


@dataclass(frozen=True)
class Provider:
    name: str
    env_var: str
    is_free: bool
    base_url: str | None
    model: str


PROVIDERS = [
    Provider("OpenAI", "OPENAI_API_KEY", False, None, "gpt-4o-mini"),
    Provider(
        "OpenRouter",
        "OPENROUTER_API_KEY",
        True,
        "https://openrouter.ai/api/v1",
        "openai/gpt-4o",
    ),
    Provider(
        "Groq",
        "GROQ_API_KEY",
        True,
        "https://api.groq.com/openai/v1",
        "openai/gpt-oss-20b",
    ),
]


def select_provider() -> Provider:
    for provider in PROVIDERS:
        if os.getenv(provider.env_var):
            return provider

    raise RuntimeError("No provider found")


def build_chat_model() -> tuple[ChatOpenAI, Provider]:
    provider = select_provider()

    kwargs: dict = {
        "model": provider.model,
        "api_key": os.getenv(provider.env_var),
    }

    if provider.base_url is not None:
        kwargs["base_url"] = provider.base_url

    return ChatOpenAI(**kwargs), provider
