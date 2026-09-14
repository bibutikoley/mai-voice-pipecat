"""OpenAI-compatible LLM provider.

Works with OpenAI and any OpenAI-compatible endpoint (vLLM, LM Studio, Ollama's
OpenAI endpoint, Groq, ...) using `LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL`.
"""

from __future__ import annotations

from pipecat.services.openai.llm import OpenAILLMService

from mai_voice.config import Settings


def create(settings: Settings) -> OpenAILLMService:
    return OpenAILLMService(
        api_key=settings.llm_api_key,
        base_url=settings.llm_base_url,
        settings=OpenAILLMService.Settings(model=settings.llm_model),
    )
