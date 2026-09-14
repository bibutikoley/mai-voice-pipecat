"""Cartesia TTS provider (cloud). Requires the `cloud` extra."""

from __future__ import annotations

from pipecat.services.cartesia.tts import CartesiaTTSService

from mai_voice.config import Settings


def create(settings: Settings) -> CartesiaTTSService:
    return CartesiaTTSService(api_key=settings.cartesia_api_key)
