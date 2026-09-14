"""Cartesia TTS provider (cloud). Requires the `cloud` extra."""

from __future__ import annotations

from pipecat.services.cartesia.tts import CartesiaTTSService

from mai_voice.config import Settings
from mai_voice.processors.text_filters import build_text_filters


def create(settings: Settings) -> CartesiaTTSService:
    return CartesiaTTSService(
        api_key=settings.cartesia_api_key,
        text_filters=build_text_filters(settings.tts_text_filters),
    )
