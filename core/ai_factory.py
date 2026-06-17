import os
from core.ai_provider import AIProvider
from core.gemini_provider import GeminiProvider
from core.groq_provider import GroqProvider


def get_ai_provider(provider_name: str = None) -> AIProvider:
    if provider_name is None:
        provider_name = os.environ.get("AI_PROVIDER", "groq")

    if provider_name == "gemini":
        return GeminiProvider()
    elif provider_name == "groq":
        return GroqProvider()
    else:
        return GeminiProvider()