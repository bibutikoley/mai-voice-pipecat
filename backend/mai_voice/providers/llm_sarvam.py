"""Sarvam AI LLM provider (OpenAI-compatible, Indic languages).

Requires the `sarvam` extra (build with `EXTRAS=sarvam`) and `SARVAM_API_KEY`.
The service adds Sarvam's `api-subscription-key` header on top of the standard
OpenAI auth, and picks its API version from the model.
"""

from __future__ import annotations

from pipecat.services.sarvam.llm import SarvamLLMService

from mai_voice.config import Settings


def create(settings: Settings) -> SarvamLLMService:
    return SarvamLLMService(
        api_key=settings.sarvam_api_key,
        settings=SarvamLLMService.Settings(model=settings.sarvam_llm_model),
    )
