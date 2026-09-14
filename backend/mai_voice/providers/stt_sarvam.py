"""Sarvam AI STT provider (cloud, WebSocket streaming, Indic languages).

Requires the `sarvam` extra (build with `EXTRAS=sarvam`) and `SARVAM_API_KEY`.
"""

from __future__ import annotations

from pipecat.services.sarvam.stt import SarvamSTTService

from mai_voice.config import Settings
from mai_voice.providers._languages import pipecat_language


def create(settings: Settings) -> SarvamSTTService:
    return SarvamSTTService(
        api_key=settings.sarvam_api_key,
        settings=SarvamSTTService.Settings(
            model=settings.sarvam_stt_model,
            language=pipecat_language(settings.sarvam_language),
        ),
    )
