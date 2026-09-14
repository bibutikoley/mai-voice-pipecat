"""Gemini STT provider (cloud, Gemini Live transcription models).

Requires the `google` extra (build with `EXTRAS=google`) and `GEMINI_API_KEY`.
The model auto-detects the spoken language unless `GEMINI_STT_LANGUAGE` is set.
"""

from __future__ import annotations

from pipecat.services.google.gemini_live.stt import GeminiSTTService

from mai_voice.config import Settings
from mai_voice.providers._languages import pipecat_language


def create(settings: Settings) -> GeminiSTTService:
    service_settings = GeminiSTTService.Settings(model=settings.gemini_stt_model)
    if settings.gemini_stt_language:
        service_settings.language = pipecat_language(settings.gemini_stt_language)
    return GeminiSTTService(
        api_key=settings.gemini_api_key,
        settings=service_settings,
    )
