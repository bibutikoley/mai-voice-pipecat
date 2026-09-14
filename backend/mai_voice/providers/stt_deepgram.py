"""Deepgram STT provider (cloud). Requires the `cloud` extra."""

from __future__ import annotations

from pipecat.services.deepgram.stt import DeepgramSTTService

from mai_voice.config import Settings


def create(settings: Settings) -> DeepgramSTTService:
    return DeepgramSTTService(api_key=settings.deepgram_api_key)
